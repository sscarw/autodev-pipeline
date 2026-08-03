import asyncio
import github_client
from coding_agent import run_coding_agent
from models import Ticket


def get_new_comments(pr_number: int, seen_ids: set[int]) -> list[dict]:
    comments = github_client.get_pr_comments(pr_number)
    new_comments = []
    for comment in comments:
        if comment["id"] not in seen_ids:
            new_comments.append(comment)

    return new_comments

def format_comments_as_instructions(comments: list[dict]) -> str:
    return "\n".join(
        comment["body"]
        for comment in comments
    )

async def wait_for_human_review(pr_number: int, ticket: Ticket, local_path: str, branch_name: str, poll_seconds: int = 30) -> None:
    seen_ids: set[int] = set()
    while True:
        if github_client.is_pr_merged(pr_number):
            return
        new_comments = get_new_comments(pr_number, seen_ids)

        if new_comments:
            instructions = format_comments_as_instructions(new_comments)

            await run_coding_agent(
                ticket,
                local_path,
                extra_instructions=instructions,
            )

            github_client.commit_and_push(
                local_path,
                branch_name,
                "fix: address review comments"
            )

            for comment in new_comments:
                seen_ids.add(comment["id"])

        await asyncio.sleep(poll_seconds)