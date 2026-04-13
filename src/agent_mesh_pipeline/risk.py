"""Filter signals → ApprovedIntent v1 → Redis Streams (see sibling `agent-mesh-signal`)."""


def run_risk_loop() -> None:
    raise NotImplementedError(
        "Production path: agent-mesh-signal (LLM + Mem0 + risk gate → XADD). "
        "Dev path: scripts/dev_publish_intent.py"
    )
