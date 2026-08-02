from models import Ticket
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from github_client import _resolve_path
from dotenv import load_dotenv

load_dotenv()


def extract_text_from_adf(description: dict | None) -> str:
    if description is None:
        return ""

    if "text" in description:
        return description["text"]

    if "content" in description:
        parts = []

        for item in description["content"]:
            text = extract_text_from_adf(item)

            if text:
                parts.append(text)

        return " ".join(parts)

    return ""


def build_prompt(ticket: Ticket) -> str:
    description = extract_text_from_adf(ticket.description)

    return (
        f"Implement the following task: {ticket.summary}. "
        f"Details: {description}"
    )


async def run_coding_agent(ticket: Ticket, local_path: str) -> None:
    options = ClaudeAgentOptions(
        cwd=_resolve_path(local_path),
        allowed_tools=["Read", "Write", "Edit", "Bash"],
        permission_mode="acceptEdits",
    )

    async for message in query(
            prompt=build_prompt(ticket),
            options=options,
    ):
        if hasattr(message, "result"):
            print(message.result)
        else:
            print(message)
