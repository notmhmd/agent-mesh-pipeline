# agent-mesh-pipeline

Python workers:

- **feed** — Alpaca market data → snapshots
- **signal** — features + rules/model → `Signal` (contracts repo)
- **risk** — limits → `ApprovedIntent` on Redis for `agent-mesh-execution`

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Dev publisher (feeds execution queue)

With Redis on localhost:

```bash
pip install -r requirements.txt
REDIS_HOST=localhost python scripts/dev_publish_intent.py
```

Docker: see `agent-mesh-infra` `pipeline` service.

## Run (stubs)

```bash
python -c "from agent_mesh_pipeline.feed import run_feed_loop; run_feed_loop()"
```

## Related

- `agent-mesh-contracts` — schemas
- `agent-mesh-execution` — .NET gateway
- `agent-mesh-infra` — compose
