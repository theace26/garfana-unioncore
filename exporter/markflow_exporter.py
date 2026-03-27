"""
MarkFlow Prometheus Exporter

Bridges MarkFlow's /api/admin/system/metrics and /api/health endpoints
to Prometheus metric format. Scrapes MarkFlow every 30 seconds and
exposes metrics on :9101/metrics.
"""

import logging
import os
import time

import httpx
from prometheus_client import Gauge, Info, start_http_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("markflow-exporter")

MARKFLOW_URL = os.environ.get("MARKFLOW_URL", "http://host.docker.internal:8000")
SCRAPE_INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", "30"))

# --- Prometheus metrics ---

# CPU metrics
cpu_percent = Gauge("markflow_cpu_percent", "MarkFlow process CPU usage percent")
cpu_count = Gauge("markflow_cpu_count", "Number of CPU cores available")

# Memory metrics
memory_rss_bytes = Gauge("markflow_memory_rss_bytes", "Resident set size in bytes")
memory_vms_bytes = Gauge("markflow_memory_vms_bytes", "Virtual memory size in bytes")
memory_percent = Gauge("markflow_memory_percent", "Process memory usage percent")

# I/O metrics
io_read_bytes = Gauge("markflow_io_read_bytes_total", "Cumulative I/O read bytes")
io_write_bytes = Gauge("markflow_io_write_bytes_total", "Cumulative I/O write bytes")

# Thread metrics
thread_count = Gauge("markflow_thread_count", "Number of active threads")

# Health check
health_up = Gauge("markflow_up", "Whether MarkFlow is healthy (1=up, 0=down)")
health_uptime = Gauge("markflow_uptime_seconds", "MarkFlow uptime in seconds")

# Component health
component_health = Gauge(
    "markflow_component_health",
    "Health status of MarkFlow components (1=healthy, 0=unhealthy)",
    ["component"],
)

# Application info
app_info = Info("markflow", "MarkFlow application information")

# Scrape metrics
scrape_duration = Gauge("markflow_scrape_duration_seconds", "Time taken to scrape MarkFlow")
scrape_errors = Gauge("markflow_scrape_errors_total", "Total number of scrape errors")

error_count = 0


def scrape_health(client: httpx.Client) -> None:
    """Scrape /api/health and update health metrics."""
    try:
        resp = client.get(f"{MARKFLOW_URL}/api/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            health_up.set(1)

            uptime = data.get("uptime_seconds", 0)
            health_uptime.set(uptime)

            # Component health from the envelope
            components = data.get("components", {})
            for name, status in components.items():
                if isinstance(status, str):
                    component_health.labels(component=name).set(
                        1 if status == "ok" else 0
                    )
                elif isinstance(status, dict):
                    component_health.labels(component=name).set(
                        1 if status.get("status") == "ok" else 0
                    )
        else:
            health_up.set(0)
    except Exception as e:
        logger.warning("Health scrape failed: %s", e)
        health_up.set(0)


def scrape_system_metrics(client: httpx.Client) -> None:
    """Scrape /api/admin/system/metrics and update system metrics."""
    try:
        resp = client.get(f"{MARKFLOW_URL}/api/admin/system/metrics", timeout=10)
        if resp.status_code == 200:
            data = resp.json()

            # CPU
            if "cpu_percent" in data:
                cpu_percent.set(data["cpu_percent"])
            if "cpu_count" in data:
                cpu_count.set(data["cpu_count"])

            # Memory
            if "memory_rss" in data:
                memory_rss_bytes.set(data["memory_rss"])
            if "memory_vms" in data:
                memory_vms_bytes.set(data["memory_vms"])
            if "memory_percent" in data:
                memory_percent.set(data["memory_percent"])

            # I/O
            if "io_read_bytes" in data:
                io_read_bytes.set(data["io_read_bytes"])
            if "io_write_bytes" in data:
                io_write_bytes.set(data["io_write_bytes"])

            # Threads
            if "threads" in data:
                thread_count.set(data["threads"])

            # Per-core CPU (if available)
            per_core = data.get("per_core_cpu", [])
            for i, pct in enumerate(per_core):
                Gauge(
                    f"markflow_cpu_core_{i}_percent",
                    f"CPU usage for core {i}",
                ).set(pct)

        elif resp.status_code == 403:
            logger.warning(
                "System metrics returned 403 - ensure DEV_BYPASS_AUTH=true or provide credentials"
            )
        else:
            logger.warning("System metrics returned %d", resp.status_code)
    except Exception as e:
        logger.warning("System metrics scrape failed: %s", e)


def collect() -> None:
    """Run one collection cycle."""
    global error_count
    start = time.time()

    try:
        with httpx.Client() as client:
            scrape_health(client)
            scrape_system_metrics(client)
    except Exception as e:
        error_count += 1
        scrape_errors.set(error_count)
        logger.error("Collection cycle failed: %s", e)

    elapsed = time.time() - start
    scrape_duration.set(elapsed)


def main() -> None:
    port = int(os.environ.get("EXPORTER_PORT", "9101"))
    logger.info("Starting MarkFlow exporter on :%d (target: %s)", port, MARKFLOW_URL)
    logger.info("Scrape interval: %ds", SCRAPE_INTERVAL)

    app_info.info({"version": "1.0.0", "target": MARKFLOW_URL})

    start_http_server(port)
    logger.info("Prometheus metrics server started on :%d", port)

    while True:
        collect()
        time.sleep(SCRAPE_INTERVAL)


if __name__ == "__main__":
    main()
