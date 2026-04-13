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

## Alpaca WSS feed → Redis

Requires `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`. Writes latest `mesh:alpaca:last:{SYMBOL}` (JSON: last bid/ask/mid/trade, timestamps).

```bash
export APCA_API_KEY_ID=... APCA_API_SECRET_KEY=...
export REDIS_HOST=localhost ALPACA_SYMBOLS=SPY,QQQ
python -m agent_mesh_pipeline.feed
```

Optional: `ALPACA_WS_URL` (default IEX `wss://stream.data.alpaca.markets/v2/iex`), `ALPACA_SUBSCRIBE_BARS=1`, `REDIS_QUOTE_KEY_PREFIX`.

Docker (`agent-mesh-infra`): `PIPELINE_CMD=alpaca` on the `pipeline` service runs the feed instead of the dev XADD loop.

## Run (other stubs)

```bash
python -c "from agent_mesh_pipeline.signal import run_signal_loop; run_signal_loop()"
```

## Related

- `agent-mesh-contracts` — schemas
- `agent-mesh-execution` — .NET gateway
- `agent-mesh-infra` — compose
