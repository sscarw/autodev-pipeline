import json
from datetime import datetime, timezone
from pathlib import Path

EVENT_LOG_PATH = Path(__file__).resolve().parent / "pipeline_events.jsonl"

# Stages shown on the dashboard kanban board, in display order.
STAGES = ["Coding", "Auto-Review", "Awaiting Human Review", "Merged"]

# Maps an event_type to the kanban stage it puts the ticket into.
_EVENT_TO_STAGE = {
    "ticket_picked_up": "Coding",
    "coding_started": "Coding",
    "coding_finished": "Coding",
    "revision_requested": "Coding",
    "review_started": "Auto-Review",
    "auto_review_verdict_request_changes": "Auto-Review",
    "auto_review_verdict_approve": "Awaiting Human Review",
    "pr_opened": "Awaiting Human Review",
    "human_comment_detected": "Awaiting Human Review",
    "agent_replied_to_comment": "Awaiting Human Review",
    "pr_merged": "Merged",
}


def append_event(
    ticket_key: str,
    event_type: str,
    message: str,
    data: dict | None = None,
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticket_key": ticket_key,
        "event_type": event_type,
        "message": message,
        "data": data or {},
    }
    with open(EVENT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def read_events(ticket_key: str | None = None, limit: int | None = None) -> list[dict]:
    if not EVENT_LOG_PATH.exists():
        return []

    events = []
    with open(EVENT_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if ticket_key is None or event["ticket_key"] == ticket_key:
                events.append(event)

    if limit is not None:
        events = events[-limit:]

    return events


def get_known_ticket_keys() -> list[str]:
    seen = []
    for event in read_events():
        if event["ticket_key"] not in seen:
            seen.append(event["ticket_key"])
    return seen


def get_latest_stage(ticket_key: str) -> str | None:
    stage = None
    for event in read_events(ticket_key=ticket_key):
        mapped = _EVENT_TO_STAGE.get(event["event_type"])
        if mapped is not None:
            stage = mapped
    return stage
