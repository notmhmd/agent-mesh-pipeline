# uv for fast, deterministic dependency installs (https://github.com/astral-sh/uv)
FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt
COPY scripts/dev_publish_intent.py ./scripts/
ENV REDIS_HOST=redis
ENV PUBLISH_INTERVAL_SEC=45
ENV STREAM_KEY=stream:approved:intents
CMD ["python", "scripts/dev_publish_intent.py"]
