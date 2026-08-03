import subprocess

from agents import Agent, Runner
from dotenv import load_dotenv

from github_client import _resolve_path
from models import ReviewResult

load_dotenv()


def get_diff(local_path: str, branch_name: str) -> str:
    target_path = _resolve_path(local_path)

    result = subprocess.run(
        [
            "git",
            "-C",
            target_path,
            "diff",
            f"main...{branch_name}",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )

    return result.stdout


review_agent = Agent(
    name="Code Reviewer",
    instructions=(
        "You are a senior software developer performing a code review. "
        "Review the provided git diff for bugs, incorrect logic, security issues, "
        "edge cases, maintainability problems, and missing error handling. "
        "Return a clear verdict and a list of specific, actionable comments. "
        "Only report issues that are visible in the diff. "
        "If there are no important problems, approve the changes and return an empty comments list."
    ),
    output_type=ReviewResult,
)


async def run_review_agent(diff: str) -> ReviewResult:
    result = await Runner.run(
        review_agent,
        f"Review this git diff:\n\n{diff}",
    )
    return result.final_output


if __name__ == "__main__":
    import asyncio

    diff = get_diff("demo-folder", "feature/ap-3-test")
    result = asyncio.run(run_review_agent(diff))
    print(result)
