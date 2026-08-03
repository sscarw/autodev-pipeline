from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"

# (key, human label, group, is_secret)
SETTINGS_FIELDS = [
    ("JIRA_URL", "Jira domain URL", "Jira", False),
    ("JIRA_EMAIL", "Jira account email", "Jira", False),
    ("JIRA_TOKEN", "Jira API token", "Jira", True),
    ("JIRA_PROJECT_KEY", "Jira project key", "Jira", False),
    ("GITHUB_TOKEN", "GitHub personal access token", "GitHub", True),
    ("GITHUB_OWNER", "GitHub repository owner", "GitHub", False),
    ("GITHUB_REPO", "GitHub repository name", "GitHub", False),
    ("REPO_URL", "GitHub repository clone URL", "GitHub", False),
    ("ANTHROPIC_API_KEY", "Anthropic API key", "LLM Providers", True),
    ("OPENAI_API_KEY", "OpenAI API key", "LLM Providers", True),
    ("LOCAL_REPO_PATH", "Local repository folder name", "Local Repository", False),
]


def read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values

    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()

    return values


def write_env_file(updates: dict[str, str]) -> None:
    existing = read_env_file()
    existing.update(updates)

    lines = [f"{key}={value}" for key, value in existing.items()]
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def _validate_url(value: str) -> str | None:
    if not value.startswith(("http://", "https://")):
        return "Must start with http:// or https://"
    if value.endswith("/"):
        return "Must not end with a trailing slash"
    return None


def _validate_email(value: str) -> str | None:
    if "@" not in value or "." not in value.split("@")[-1]:
        return "Must be a valid email address"
    return None


def _validate_no_slashes(value: str) -> str | None:
    if any(c in value for c in ("/", "\\", " ")):
        return "Must not contain slashes or spaces"
    return None


def _validate_repo_url(value: str) -> str | None:
    if not value.startswith(("http://", "https://", "git@")):
        return "Must be a git clone URL (https:// or git@...)"
    return None


def _validate_local_path(value: str) -> str | None:
    if ".." in value or "/" in value or "\\" in value:
        return "Must be a simple folder name, not a path (no '..' or slashes)"
    return None


def _validate_no_whitespace(value: str) -> str | None:
    if value != value.strip() or any(c.isspace() for c in value):
        return "Must not contain spaces or extra whitespace (check for a stray copy-paste)"
    return None


_VALIDATORS = {
    "JIRA_URL": _validate_url,
    "JIRA_EMAIL": _validate_email,
    "JIRA_TOKEN": _validate_no_whitespace,
    "GITHUB_TOKEN": _validate_no_whitespace,
    "GITHUB_OWNER": _validate_no_slashes,
    "GITHUB_REPO": _validate_no_slashes,
    "REPO_URL": _validate_repo_url,
    "ANTHROPIC_API_KEY": _validate_no_whitespace,
    "OPENAI_API_KEY": _validate_no_whitespace,
    "LOCAL_REPO_PATH": _validate_local_path,
}


def validate_fields(updates: dict[str, str]) -> dict[str, str]:
    """Validate submitted field values. Returns {field_key: error_message}
    for any values that fail validation. Empty values are always allowed,
    since settings may be filled in progressively."""
    errors: dict[str, str] = {}
    for key, value in updates.items():
        if not value:
            continue
        validator = _VALIDATORS.get(key)
        if validator is None:
            continue
        error = validator(value)
        if error is not None:
            errors[key] = error
    return errors
