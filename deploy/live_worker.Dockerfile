FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY src/live/collector.py src/live/worker.py data/yield_data.csv ./
COPY live_data/live_snapshot.example.json /app/live_data/live_snapshot.example.json
RUN useradd --create-home --uid 10001 worker && mkdir -p /app/live_data && chown -R worker:worker /app
USER worker

CMD ["python", "live_worker.py"]
