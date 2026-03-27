FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY markflow_exporter.py .

EXPOSE 9101

CMD ["python", "markflow_exporter.py"]
