from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import env_settings
import event_log
import jira_client
from models import Ticket

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="AutoDev")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

JIRA_STATUSES = ["To Do", "In Progress", "In Review", "Done"]


def _jira_is_configured() -> bool:
    values = env_settings.read_env_file()
    return bool(
        values.get("JIRA_URL")
        and values.get("JIRA_EMAIL")
        and values.get("JIRA_TOKEN")
        and values.get("JIRA_PROJECT_KEY")
    )


def _github_is_configured() -> bool:
    values = env_settings.read_env_file()
    return bool(values.get("GITHUB_TOKEN") and values.get("GITHUB_OWNER") and values.get("GITHUB_REPO"))


def get_all_jira_tickets() -> dict[str, Ticket]:
    # Skip the network calls entirely when Jira hasn't been configured yet,
    # rather than retrying (and failing) on every 5-second board refresh.
    if not _jira_is_configured():
        return {}

    tickets: dict[str, Ticket] = {}
    for status in JIRA_STATUSES:
        try:
            for ticket in jira_client.get_tickets_by_status(status):
                tickets[ticket.key] = ticket
        except httpx.HTTPError:
            # Wrong credentials, or a status doesn't exist on this board.
            continue
    return tickets


def build_board() -> dict[str, list[dict]]:
    jira_tickets = get_all_jira_tickets()
    known_keys = event_log.get_known_ticket_keys()

    board: dict[str, list[dict]] = {stage: [] for stage in event_log.STAGES}

    for key in known_keys:
        stage = event_log.get_latest_stage(key)
        if stage is None:
            continue

        events = event_log.read_events(ticket_key=key)
        last_event = events[-1] if events else None
        ticket = jira_tickets.get(key)

        board[stage].append(
            {
                "key": key,
                "summary": ticket.summary if ticket else key,
                "last_message": last_event["message"] if last_event else "",
                "last_time": last_event["timestamp"] if last_event else "",
            }
        )

    return board


def highlight_diff(diff_text: str) -> list[tuple[str, str]]:
    lines = []
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---")):
            css_class = "diff-meta"
        elif line.startswith("@@"):
            css_class = "diff-hunk"
        elif line.startswith("+"):
            css_class = "diff-add"
        elif line.startswith("-"):
            css_class = "diff-del"
        else:
            css_class = "diff-ctx"
        lines.append((css_class, line))
    return lines


def build_ticket_detail(key: str) -> dict:
    events = event_log.read_events(ticket_key=key)

    diff = None
    pr_url = None
    pr_number = None
    attempts = []
    comments = []

    for event in events:
        data = event.get("data", {})

        if "diff" in data:
            diff = data["diff"]
        if "pr_url" in data:
            pr_url = data["pr_url"]
        if "pr_number" in data:
            pr_number = data["pr_number"]

        if event["event_type"].startswith("auto_review_verdict"):
            attempts.append(
                {
                    "verdict": data.get("verdict"),
                    "summary": data.get("summary"),
                    "comments": data.get("comments", []),
                    "timestamp": event["timestamp"],
                }
            )
        elif event["event_type"] == "human_comment_detected":
            comments.append({"role": "human", "body": data.get("body"), "timestamp": event["timestamp"]})
        elif event["event_type"] == "agent_replied_to_comment":
            comments.append({"role": "agent", "body": data.get("body"), "timestamp": event["timestamp"]})

    env_values = env_settings.read_env_file()
    jira_url_base = env_values.get("JIRA_URL")
    jira_url = f"{jira_url_base}/browse/{key}" if jira_url_base else None

    jira_tickets = get_all_jira_tickets()
    ticket = jira_tickets.get(key)

    return {
        "key": key,
        "summary": ticket.summary if ticket else key,
        "stage": event_log.get_latest_stage(key),
        "diff_lines": highlight_diff(diff) if diff else None,
        "pr_url": pr_url,
        "pr_number": pr_number,
        "attempts": attempts,
        "comments": comments,
        "jira_url": jira_url,
        "events": events,
    }


@app.get("/")
def dashboard_page(request: Request):
    board = build_board()
    feed = list(reversed(event_log.read_events(limit=50)))
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "board": board,
            "stages": event_log.STAGES,
            "feed": feed,
            "needs_setup": not (_jira_is_configured() and _github_is_configured()),
        },
    )


@app.get("/partials/board")
def board_partial(request: Request):
    board = build_board()
    feed = list(reversed(event_log.read_events(limit=50)))
    return templates.TemplateResponse(
        request,
        "_board.html",
        {"board": board, "stages": event_log.STAGES, "feed": feed},
    )


@app.get("/ticket/{key}")
def ticket_detail(request: Request, key: str):
    detail = build_ticket_detail(key)
    return templates.TemplateResponse(
        request,
        "_ticket_detail.html",
        {"ticket": detail},
    )


def build_settings_groups(values: dict[str, str], errors: dict[str, str] | None = None) -> dict[str, list[dict]]:
    errors = errors or {}
    groups: dict[str, list[dict]] = {}
    for key, label, group, is_secret in env_settings.SETTINGS_FIELDS:
        raw_value = values.get(key, "")
        # Only reveal a secret's raw value when it just failed validation, so
        # the user can see exactly what to fix. Otherwise keep it masked.
        show_raw = key in errors
        display_value = raw_value if (not is_secret or show_raw) else env_settings.mask_secret(raw_value)
        groups.setdefault(group, []).append(
            {
                "key": key,
                "label": label,
                "is_secret": is_secret,
                "value": display_value,
                "error": errors.get(key),
            }
        )
    return groups


@app.get("/settings")
def settings_page(request: Request):
    current = env_settings.read_env_file()
    groups = build_settings_groups(current)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"groups": groups, "saved": request.query_params.get("saved") == "1"},
    )


@app.post("/settings")
async def save_settings(request: Request):
    form = await request.form()
    current = env_settings.read_env_file()

    submitted: dict[str, str] = {}
    for key, _label, _group, is_secret in env_settings.SETTINGS_FIELDS:
        value = form.get(key, "")
        # A masked secret left untouched is submitted back as exactly the
        # masked string we rendered; resolve it back to the real stored
        # value so we neither overwrite it nor validate the mask itself.
        if is_secret and value == env_settings.mask_secret(current.get(key, "")):
            value = current.get(key, "")
        submitted[key] = value

    errors = env_settings.validate_fields(submitted)
    if errors:
        groups = build_settings_groups(submitted, errors=errors)
        return templates.TemplateResponse(
            request,
            "settings.html",
            {"groups": groups, "saved": False, "has_errors": True},
        )

    env_settings.write_env_file(submitted)
    return RedirectResponse(url="/settings?saved=1", status_code=303)
