import os
import subprocess
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()


def _resolve_path(local_path: str) -> str:
    parent_dir = Path(__file__).resolve().parent.parent
    target_path = parent_dir / local_path
    return str(target_path)


def ensure_repo_cloned(local_path: str) -> None:
    repo_url = os.getenv("REPO_URL")

    if not repo_url:
        raise ValueError("REPO_URL must be set in .env")

    target_path = _resolve_path(local_path)

    if not Path(target_path).exists():
        print(f"There is no folder. Clone the repository to: {target_path}")

        subprocess.run(
            ["git", "clone", repo_url, target_path],
            check=True,
        )
    else:
        print(f"The folder exists. Update the main branch: {target_path}")

        subprocess.run(
            ["git", "-C", target_path, "checkout", "main"],
            check=True,
        )

        subprocess.run(
            ["git", "-C", target_path, "pull"],
            check=True,
        )


def create_branch(local_path: str, branch_name: str) -> None:
    target_path = _resolve_path(local_path)

    branch_check = subprocess.run(
        ["git", "-C", target_path, "branch", "--list", branch_name],
        capture_output=True,
        text=True,
        check=True,
    )

    if branch_check.stdout.strip():
        subprocess.run(
            ["git", "-C", target_path, "switch", branch_name],
            check=True,
        )

        print(f"Switched to existing branch: {branch_name}")
        return

    subprocess.run(
        ["git", "-C", target_path, "switch", "main"],
        check=True,
    )

    subprocess.run(
        ["git", "-C", target_path, "pull"],
        check=True,
    )

    subprocess.run(
        ["git", "-C", target_path, "switch", "-c", branch_name],
        check=True,
    )

    print(f"Created and switched to branch: {branch_name}")


def commit_and_push(local_path: str, branch_name: str, message: str) -> None:
    target_path = _resolve_path(local_path)

    subprocess.run(
        ["git", "-C", target_path, "add", "."],
        check=True,
    )

    subprocess.run(
        ["git", "-C", target_path, "commit", "-m", message],
        check=True,
    )

    subprocess.run(
        ["git", "-C", target_path, "push", "origin", "-u", branch_name],
        check=True,
    )


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")


def get_github_client() -> httpx.Client:
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN must be set in .env")

    return httpx.Client(
        base_url="https://api.github.com",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )


def create_pull_request(
        branch_name: str,
        title: str,
        body: str,
) -> dict:
    _validate_github_config()

    with get_github_client() as client:
        response = client.post(
            f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls",
            json={
                "title": title,
                "head": branch_name,
                "base": "main",
                "body": body,
            },
        )

        response.raise_for_status()
        return response.json()


def _validate_github_config() -> None:
    if not GITHUB_OWNER or not GITHUB_REPO:
        raise ValueError(
            "GITHUB_OWNER and GITHUB_REPO must be set in .env"
        )


def get_pr_comments(pr_number: int) -> list[dict]:
    _validate_github_config()

    with get_github_client() as client:
        response = client.get(
            f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
            f"/pulls/{pr_number}/comments"
        )

        response.raise_for_status()
        return response.json()


def post_pr_comment(pr_number: int, body: str) -> None:
    _validate_github_config()

    with get_github_client() as client:
        response = client.post(
            f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
            f"/issues/{pr_number}/comments",
            json={
                "body": body,
            },
        )

        response.raise_for_status()
