#!/usr/bin/env python3
"""LPUSH sample ApprovedIntent JSON for agent-mesh-execution BRPOP (dev only)."""

import json
import os
import time
import uuid

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
INTENTS_KEY = "approved:intents"
INTERVAL = float(os.getenv("PUBLISH_INTERVAL_SEC", "45"))


def main() -> None:
    r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    r.ping()
    print(f"Publishing sample intents to {INTENTS_KEY} every {INTERVAL}s → redis://{REDIS_HOST}:6379")

    n = 0
    while True:
        n += 1
        payload = {
            "schema_version": 1,
            "intent_id": str(uuid.uuid4()),
            "trace_id": f"dev-{n}",
            "symbol": "SPY",
            "side": "BUY",
            "qty": 1,
            "idempotency_key": f"dev-{uuid.uuid4()}",
            "environment": "paper",
            "created_at_unix": time.time(),
        }
        raw = json.dumps(payload, separators=(",", ":"))
        r.lpush(INTENTS_KEY, raw)
        print(f"[{n}] LPUSH {INTENTS_KEY} ({len(raw)} bytes)")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
