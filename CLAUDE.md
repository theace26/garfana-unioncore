# garfana-unioncore — CLAUDE.md

Grafana observability stack for MarkFlow (primary) with UnionCore hooks planned.

---

## What This Is

Docker Compose stack providing centralized monitoring for MarkFlow:
- **Prometheus** — metrics collection (scrapes blackbox exporter + custom MarkFlow exporter)
- **Loki** — log aggregation (structlog JSON from MarkFlow containers)
- **Promtail** — ships Docker container logs to Loki
- **Blackbox Exporter** — HTTP probing for health/latency
- **MarkFlow Exporter** — bridges MarkFlow's `/api/admin/system/metrics` to Prometheus format
- **Grafana** — 4 pre-built dashboards + alerting rules

---

## Quick Start

```bash
# 1. Ensure MarkFlow is running
cd ../Doc-Conversion-2026 && docker-compose up -d && cd ../garfana-unioncore

# 2. Copy and edit env
cp .env.example .env
# Edit MARKFLOW_LOGS_PATH if your MarkFlow project is in a different location

# 3. Start the stack
docker-compose up -d

# 4. Open Grafana
# http://localhost:3000  (admin/admin)
```

---

## Architecture

```
MarkFlow (port 8000)
  ├── /api/health ──────────► Blackbox Exporter ──► Prometheus
  ├── /api/admin/system/metrics ► MarkFlow Exporter ► Prometheus
  └── Docker stdout (structlog JSON) ► Promtail ──► Loki
                                                       │
Grafana (port 3000) ◄──── Prometheus + Loki ◄──────────┘
  ├── API Latency dashboard
  ├── Error Rates dashboard
  ├── Log Viewer dashboard
  ├── System Health dashboard
  └── Alert rules (down, CPU, memory, latency)
```

---

## Pre-Built Dashboards

| Dashboard | Data Source | What It Shows |
|-----------|-----------|---------------|
| API Latency | Prometheus + Loki | Probe duration, request timing from logs, slowest endpoints |
| Error Rates | Loki | Error counts by level, HTTP error codes, top error messages |
| Log Viewer | Loki | Full log stream with level/logger/request_id filters |
| System Health | Prometheus | CPU, memory, I/O, threads, component health, uptime |

---

## Alert Rules

| Alert | Condition | For | Severity |
|-------|-----------|-----|----------|
| MarkFlow Down | health check fails | 2 min | critical |
| Health Probe Failing | blackbox probe fails | 2 min | critical |
| High CPU | CPU > 80% | 5 min | warning |
| High Memory | Memory > 85% | 5 min | warning |
| API Latency Spike | probe > 5s | 5 min | warning |

---

## Ports

| Service | Port |
|---------|------|
| Grafana | 3000 |
| Prometheus | 9090 |
| Loki | 3100 |
| Blackbox Exporter | 9115 |
| MarkFlow Exporter | 9101 |

---

## Key Files

| File | Purpose |
|------|---------|
| docker-compose.yml | All services |
| prometheus/prometheus.yml | Scrape configs |
| loki/loki-config.yml | Loki storage + retention |
| promtail/promtail-config.yml | Log discovery + JSON parsing |
| blackbox/blackbox.yml | HTTP probe modules |
| exporter/markflow_exporter.py | Python bridge: MarkFlow API → Prometheus |
| grafana/provisioning/datasources/ | Auto-configured Prometheus + Loki |
| grafana/provisioning/dashboards/*.json | 4 pre-built dashboards |
| grafana/provisioning/alerting/alerts.yml | Alert rules + contact points |

---

## MarkFlow Integration Points

The exporter scrapes these MarkFlow endpoints (requires `DEV_BYPASS_AUTH=true` or admin credentials):
- `GET /api/health` — uptime, component status
- `GET /api/admin/system/metrics` — CPU, memory, I/O, threads

Promtail reads MarkFlow's structlog JSON from Docker container logs. Key fields:
`level`, `event`, `logger`, `method`, `path`, `status_code`, `duration_ms`, `request_id`

---

## UnionCore Integration (Future)

When UnionCore is ready:
1. Add its endpoints to `prometheus/prometheus.yml` blackbox targets
2. Add a second exporter instance or extend `markflow_exporter.py`
3. Add Promtail relabel rules for UnionCore container names
4. Create UnionCore-specific dashboards in `grafana/provisioning/dashboards/`
5. Add UnionCore alert rules to `grafana/provisioning/alerting/alerts.yml`

---

## Troubleshooting

**Promtail can't read Docker logs:**
Docker socket must be accessible. On Windows Docker Desktop, `/var/run/docker.sock`
is available inside WSL2/Docker containers by default.

**Exporter shows 403 from MarkFlow:**
MarkFlow needs `DEV_BYPASS_AUTH=true` in its env, or the exporter needs auth headers.

**No data in Grafana:**
1. Check Prometheus targets: http://localhost:9090/targets
2. Check Loki: http://localhost:3100/ready
3. Check exporter: http://localhost:9101/metrics

**host.docker.internal not resolving:**
This is Docker Desktop only (Windows/Mac). On Linux, use `172.17.0.1` or the host IP.
