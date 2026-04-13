"""Alpaca market data (WSS) → latest quote/trade snapshots in Redis."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import redis
from websocket import WebSocketApp

logger = logging.getLogger("agent_mesh_pipeline.feed")


def _redis() -> redis.Redis:
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    return redis.Redis(host=host, port=port, db=db, decode_responses=True)


def _symbols() -> list[str]:
    raw = os.getenv("ALPACA_SYMBOLS", os.getenv("FEED_SYMBOLS", "SPY"))
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def _ws_url() -> str:
    return os.getenv(
        "ALPACA_WS_URL",
        "wss://stream.data.alpaca.markets/v2/iex",
    ).strip()


def _quote_key(symbol: str) -> str:
    prefix = os.getenv("REDIS_QUOTE_KEY_PREFIX", "mesh:alpaca:last:").rstrip(":")
    return f"{prefix}:{symbol}"


def _snapshot_from_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Turn Alpaca stream datum into a small JSON-serializable snapshot update."""
    t = msg.get("T")
    if t == "t":
        sym = str(msg.get("S", "")).upper()
        if not sym:
            return None
        price = msg.get("p")
        if price is None:
            return None
        return {
            "symbol": sym,
            "last_price": float(price),
            "event": "trade",
            "ts": msg.get("t"),
        }
    if t == "q":
        sym = str(msg.get("S", "")).upper()
        if not sym:
            return None
        bp = msg.get("bp")
        ap = msg.get("ap")
        if bp is None or ap is None:
            return None
        bid = float(bp)
        ask = float(ap)
        return {
            "symbol": sym,
            "bid": bid,
            "ask": ask,
            "mid": (bid + ask) / 2.0,
            "event": "quote",
            "ts": msg.get("t"),
        }
    if t == "b":
        sym = str(msg.get("S", "")).upper()
        if not sym:
            return None
        c = msg.get("c")
        if c is None:
            return None
        return {
            "symbol": sym,
            "bar_close": float(c),
            "bar_open": float(msg["o"]) if msg.get("o") is not None else None,
            "bar_high": float(msg["h"]) if msg.get("h") is not None else None,
            "bar_low": float(msg["l"]) if msg.get("l") is not None else None,
            "volume": int(msg["v"]) if msg.get("v") is not None else None,
            "event": "bar",
            "ts": msg.get("t"),
        }
    return None


def merge_snapshot(
    prior: dict[str, Any] | None, update: dict[str, Any]
) -> dict[str, Any]:
    """Merge a new datum into the rolling per-symbol document."""
    base: dict[str, Any] = dict(prior) if prior else {}
    sym = update["symbol"]
    base["symbol"] = sym
    ev = update.get("event")
    if ev == "trade":
        base["last_price"] = update["last_price"]
        base["last_trade_ts"] = update.get("ts")
    elif ev == "quote":
        base["bid"] = update["bid"]
        base["ask"] = update["ask"]
        base["mid"] = update["mid"]
        base["quote_ts"] = update.get("ts")
    elif ev == "bar":
        base["bar_close"] = update["bar_close"]
        for k in ("bar_open", "bar_high", "bar_low", "volume"):
            if update.get(k) is not None:
                base[k] = update[k]
        base["bar_ts"] = update.get("ts")
    base["updated_at_unix"] = time.time()
    base["source"] = "alpaca_wss"
    return base


def run_feed_loop() -> None:
    """Connect to Alpaca stock stream (WSS), subscribe, write latest state to Redis."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    key_id = (os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY_ID") or "").strip()
    secret = (os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_API_SECRET_KEY") or "").strip()
    if not key_id or not secret:
        raise RuntimeError(
            "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY (Alpaca market data credentials)."
        )

    symbols = _symbols()
    if not symbols:
        raise RuntimeError("ALPACA_SYMBOLS (or FEED_SYMBOLS) must list at least one ticker.")

    url = _ws_url()
    r = _redis()
    r.ping()

    subscribe_bars = os.getenv("ALPACA_SUBSCRIBE_BARS", "0").lower() in (
        "1",
        "true",
        "yes",
    )
    state: dict[str, dict[str, Any]] = {}
    subscribed = False

    def on_message(_ws: WebSocketApp, message: str) -> None:
        nonlocal subscribed
        try:
            batch = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("non-json message: %s", message[:200])
            return
        if not isinstance(batch, list):
            batch = [batch]
        for item in batch:
            if not isinstance(item, dict):
                continue
            if item.get("T") == "error":
                logger.error("alpaca stream error: %s", item)
                continue
            if (
                item.get("T") == "success"
                and item.get("msg") == "authenticated"
                and not subscribed
            ):
                body: dict[str, Any] = {
                    "action": "subscribe",
                    "trades": symbols,
                    "quotes": symbols,
                }
                if subscribe_bars:
                    body["bars"] = symbols
                _ws.send(json.dumps(body))
                subscribed = True
                logger.info("subscribed trades/quotes%s", " + bars" if subscribe_bars else "")
                continue
            snap = _snapshot_from_message(item)
            if snap is None:
                continue
            sym = snap["symbol"]
            merged = merge_snapshot(state.get(sym), snap)
            state[sym] = merged
            key = _quote_key(sym)
            r.set(key, json.dumps(merged, separators=(",", ":")))
            logger.debug("SET %s", key)

    def on_error(_ws: WebSocketApp, error: object) -> None:
        logger.error("websocket error: %s", error)

    def on_close(
        _ws: WebSocketApp,
        close_status_code: int | None,
        close_msg: str | None,
    ) -> None:
        logger.warning("websocket closed code=%s msg=%s", close_status_code, close_msg)

    def on_open(ws: WebSocketApp) -> None:
        nonlocal subscribed
        subscribed = False
        ws.send(json.dumps({"action": "auth", "key": key_id, "secret": secret}))
        logger.info("connected %s, sent auth", url)

    reconnect_sec = float(os.getenv("ALPACA_WS_RECONNECT_SEC", "5"))
    while True:
        try:
            ws = WebSocketApp(
                url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            ws.run_forever(
                ping_interval=20,
                ping_timeout=10,
            )
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.exception("run_forever failed")
        logger.info("reconnecting in %.1fs", reconnect_sec)
        time.sleep(reconnect_sec)


if __name__ == "__main__":
    run_feed_loop()
