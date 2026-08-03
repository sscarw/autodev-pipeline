import event_log


def test_append_and_read_events(tmp_path, monkeypatch):
    monkeypatch.setattr(event_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")

    event_log.append_event("AUT-1", "ticket_picked_up", "picked up")
    event_log.append_event("AUT-1", "coding_started", "coding")
    event_log.append_event("AUT-2", "ticket_picked_up", "picked up")

    all_events = event_log.read_events()
    assert len(all_events) == 3

    aut1_events = event_log.read_events(ticket_key="AUT-1")
    assert len(aut1_events) == 2
    assert all(e["ticket_key"] == "AUT-1" for e in aut1_events)


def test_read_events_returns_empty_list_when_log_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(event_log, "EVENT_LOG_PATH", tmp_path / "missing.jsonl")
    assert event_log.read_events() == []


def test_get_known_ticket_keys_preserves_first_seen_order(tmp_path, monkeypatch):
    monkeypatch.setattr(event_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")

    event_log.append_event("AUT-2", "ticket_picked_up", "picked up")
    event_log.append_event("AUT-1", "ticket_picked_up", "picked up")
    event_log.append_event("AUT-2", "coding_started", "coding")

    assert event_log.get_known_ticket_keys() == ["AUT-2", "AUT-1"]


def test_get_latest_stage_tracks_the_most_recent_mapped_event(tmp_path, monkeypatch):
    monkeypatch.setattr(event_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")

    event_log.append_event("AUT-1", "ticket_picked_up", "picked up")
    assert event_log.get_latest_stage("AUT-1") == "Coding"

    event_log.append_event("AUT-1", "auto_review_verdict_approve", "approved")
    assert event_log.get_latest_stage("AUT-1") == "Awaiting Human Review"

    event_log.append_event("AUT-1", "pr_merged", "merged")
    assert event_log.get_latest_stage("AUT-1") == "Merged"


def test_get_latest_stage_returns_none_for_unknown_ticket(tmp_path, monkeypatch):
    monkeypatch.setattr(event_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    assert event_log.get_latest_stage("NOPE") is None
