"""Unit tests for Alpaca WSS feed normalization (no live socket)."""

from agent_mesh_pipeline.feed import merge_snapshot, _snapshot_from_message


def test_trade_snapshot() -> None:
    msg = {
        "T": "t",
        "S": "SPY",
        "p": 450.12,
        "t": "2025-01-01T15:00:00Z",
    }
    s = _snapshot_from_message(msg)
    assert s is not None
    assert s["symbol"] == "SPY"
    assert s["last_price"] == 450.12
    assert s["event"] == "trade"


def test_quote_snapshot_mid() -> None:
    msg = {
        "T": "q",
        "S": "SPY",
        "bp": 100.0,
        "ap": 100.2,
        "t": "2025-01-01T15:00:01Z",
    }
    s = _snapshot_from_message(msg)
    assert s is not None
    assert s["mid"] == 100.1
    assert s["bid"] == 100.0
    assert s["ask"] == 100.2


def test_merge_trade_then_quote() -> None:
    t = _snapshot_from_message(
        {"T": "t", "S": "AAPL", "p": 200.0, "t": "2025-01-01T15:00:00Z"}
    )
    assert t is not None
    m1 = merge_snapshot(None, t)
    assert m1["last_price"] == 200.0
    q = _snapshot_from_message(
        {
            "T": "q",
            "S": "AAPL",
            "bp": 199.9,
            "ap": 200.1,
            "t": "2025-01-01T15:00:01Z",
        }
    )
    assert q is not None
    m2 = merge_snapshot(m1, q)
    assert m2["last_price"] == 200.0
    assert m2["mid"] == 200.0
    assert m2["source"] == "alpaca_wss"
