import pytest
from fastapi.testclient import TestClient

import dashboard
import env_settings
import event_log


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Isolate every test from the real .env and pipeline_events.jsonl on disk.
    monkeypatch.setattr(env_settings, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(event_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    return TestClient(dashboard.app)


def test_dashboard_page_loads_with_no_data(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Pipeline Dashboard" in response.text
    assert "No pipeline activity yet" in response.text


def test_dashboard_shows_setup_hint_when_unconfigured(client):
    response = client.get("/")
    assert "finish setup in Settings" in response.text


def test_dashboard_hides_setup_hint_once_configured(client, monkeypatch):
    # Fully configured, but avoid a real network call to a fake Jira domain.
    monkeypatch.setattr(dashboard.jira_client, "get_tickets_by_status", lambda status: [])
    env_settings.write_env_file(
        {
            "JIRA_URL": "https://example.atlassian.net",
            "JIRA_EMAIL": "user@example.com",
            "JIRA_TOKEN": "token",
            "JIRA_PROJECT_KEY": "AUT",
            "GITHUB_TOKEN": "token",
            "GITHUB_OWNER": "sscarw",
            "GITHUB_REPO": "autodev-demo-target",
        }
    )
    response = client.get("/")
    assert "finish setup in Settings" not in response.text


def test_settings_page_loads_with_empty_fields(client):
    response = client.get("/settings")
    assert response.status_code == 200
    assert "Settings" in response.text


def test_ticket_detail_for_unknown_key_does_not_crash(client):
    response = client.get("/ticket/UNKNOWN-1")
    assert response.status_code == 200
    assert "No diff recorded yet" in response.text


def test_save_settings_rejects_invalid_local_repo_path(client):
    response = client.post("/settings", data={"LOCAL_REPO_PATH": "../../etc"})
    assert response.status_code == 200
    assert "look wrong" in response.text
    assert env_settings.read_env_file().get("LOCAL_REPO_PATH", "") == ""


def test_save_settings_accepts_valid_values(client):
    response = client.post(
        "/settings",
        data={"JIRA_URL": "https://example.atlassian.net", "LOCAL_REPO_PATH": "demo-folder"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/settings?saved=1"

    saved = env_settings.read_env_file()
    assert saved["JIRA_URL"] == "https://example.atlassian.net"
    assert saved["LOCAL_REPO_PATH"] == "demo-folder"


def test_board_reflects_events_for_a_ticket(client):
    event_log.append_event("AUT-1", "ticket_picked_up", "Agent picked up ticket")
    event_log.append_event("AUT-1", "pr_merged", "Merged", {"pr_url": "https://example.com/pr/1"})

    response = client.get("/")
    assert response.status_code == 200
    assert "AUT-1" in response.text
