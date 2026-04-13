FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/dev_publish_intent.py ./scripts/
ENV REDIS_HOST=redis
ENV PUBLISH_INTERVAL_SEC=45
CMD ["python", "scripts/dev_publish_intent.py"]
