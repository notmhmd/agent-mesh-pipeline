# uv for fast, deterministic dependency installs (https://github.com/astral-sh/uv)
FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
RUN uv pip install --system -e .
ENV REDIS_HOST=redis
ENV PUBLISH_INTERVAL_SEC=45
ENV STREAM_KEY=stream:approved:intents
# dev: periodic XADD sample intents | alpaca: WSS market data → Redis mesh:alpaca:last:*
ENV PIPELINE_CMD=dev
CMD ["sh", "-c", "if [ \"$PIPELINE_CMD\" = \"alpaca\" ]; then python -m agent_mesh_pipeline.feed; else python scripts/dev_publish_intent.py; fi"]
