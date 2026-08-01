from dotenv import load_dotenv
import httpx
import os
from models import Ticket

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")


def get_client():
    return httpx.Client(base_url=JIRA_URL, auth=(JIRA_EMAIL, JIRA_TOKEN))


def get_tickets_by_status(status: str) -> list[Ticket]:
    jql = f'project = "{JIRA_PROJECT_KEY}" AND status = "{status}"'

    with get_client() as client:
        response = client.post(
            "/rest/api/3/search/jql",
            json={
                "jql": jql,
                "fields": ["summary", "description", "status"],
                "maxResults": 100,
            },
        )

        response.raise_for_status()
        issues = response.json().get("issues", [])

    tickets = []

    for issue in issues:
        fields = issue["fields"]

        tickets.append(
            Ticket(
                key=issue["key"],
                summary=fields["summary"],
                description=fields.get("description"),
                status=fields["status"]["name"],
            )
        )

    return tickets


def get_available_transitions(ticket_key: str) -> dict[str, str]:
    with get_client() as client:
        response = client.get(
            f"/rest/api/3/issue/{ticket_key}/transitions"
        )

        response.raise_for_status()

        data = response.json()

        transitions = data.get("transitions", [])

        return {
            transition["to"]["name"]: transition["id"]
            for transition in transitions
        }


def transition_ticket(ticket_key: str, new_status: str) -> None:
    transitions = get_available_transitions(ticket_key)

    transition_id = transitions.get(new_status)

    if transition_id is None:
        available = ", ".join(transitions.keys())
        raise ValueError(
            f"Transition to '{new_status}' is not available. "
            f"Available statuses: {available}"
        )

    with get_client() as client:
        response = client.post(
            f"/rest/api/3/issue/{ticket_key}/transitions",
            json={
                "transition": {
                    "id": transition_id,
                }
            },
        )

        response.raise_for_status()
