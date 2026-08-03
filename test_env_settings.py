import env_settings


def test_write_then_read_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(env_settings, "ENV_PATH", tmp_path / ".env")

    env_settings.write_env_file({"JIRA_URL": "https://example.atlassian.net"})
    assert env_settings.read_env_file() == {"JIRA_URL": "https://example.atlassian.net"}


def test_write_env_file_updates_only_given_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(env_settings, "ENV_PATH", tmp_path / ".env")

    env_settings.write_env_file({"JIRA_URL": "https://a.atlassian.net", "GITHUB_OWNER": "sscarw"})
    env_settings.write_env_file({"JIRA_URL": "https://b.atlassian.net"})

    values = env_settings.read_env_file()
    assert values["JIRA_URL"] == "https://b.atlassian.net"
    assert values["GITHUB_OWNER"] == "sscarw"


def test_read_env_file_returns_empty_dict_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(env_settings, "ENV_PATH", tmp_path / "missing.env")
    assert env_settings.read_env_file() == {}


def test_read_env_file_ignores_comments_and_blank_lines(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("# a comment\n\nJIRA_URL=https://example.atlassian.net\n")
    monkeypatch.setattr(env_settings, "ENV_PATH", env_path)

    assert env_settings.read_env_file() == {"JIRA_URL": "https://example.atlassian.net"}


def test_mask_secret_keeps_first_and_last_four_characters():
    secret = "sk-ant-api03-abcdefgh"
    masked = env_settings.mask_secret(secret)
    assert masked == "sk-a" + "*" * (len(secret) - 8) + "efgh"


def test_mask_secret_fully_masks_short_values():
    assert env_settings.mask_secret("abc") == "***"


def test_mask_secret_empty_string():
    assert env_settings.mask_secret("") == ""


def test_validate_fields_allows_empty_values():
    errors = env_settings.validate_fields({"JIRA_URL": "", "JIRA_EMAIL": ""})
    assert errors == {}


def test_validate_fields_rejects_url_without_scheme():
    errors = env_settings.validate_fields({"JIRA_URL": "example.atlassian.net"})
    assert "JIRA_URL" in errors


def test_validate_fields_rejects_url_with_trailing_slash():
    errors = env_settings.validate_fields({"JIRA_URL": "https://example.atlassian.net/"})
    assert "JIRA_URL" in errors


def test_validate_fields_accepts_valid_url():
    errors = env_settings.validate_fields({"JIRA_URL": "https://example.atlassian.net"})
    assert "JIRA_URL" not in errors


def test_validate_fields_rejects_invalid_email():
    errors = env_settings.validate_fields({"JIRA_EMAIL": "not-an-email"})
    assert "JIRA_EMAIL" in errors


def test_validate_fields_accepts_valid_email():
    errors = env_settings.validate_fields({"JIRA_EMAIL": "user@example.com"})
    assert "JIRA_EMAIL" not in errors


def test_validate_fields_rejects_slashes_in_owner_and_repo():
    errors = env_settings.validate_fields({"GITHUB_OWNER": "sscarw/evil", "GITHUB_REPO": "some repo"})
    assert "GITHUB_OWNER" in errors
    assert "GITHUB_REPO" in errors


def test_validate_fields_rejects_path_traversal_in_local_repo_path():
    errors = env_settings.validate_fields({"LOCAL_REPO_PATH": "../../etc"})
    assert "LOCAL_REPO_PATH" in errors


def test_validate_fields_accepts_simple_local_repo_path():
    errors = env_settings.validate_fields({"LOCAL_REPO_PATH": "demo-folder"})
    assert "LOCAL_REPO_PATH" not in errors


def test_validate_fields_rejects_whitespace_in_secret():
    errors = env_settings.validate_fields({"ANTHROPIC_API_KEY": "sk-ant- api03-xyz"})
    assert "ANTHROPIC_API_KEY" in errors


def test_validate_fields_rejects_repo_url_without_valid_scheme():
    errors = env_settings.validate_fields({"REPO_URL": "not-a-url"})
    assert "REPO_URL" in errors


def test_validate_fields_accepts_ssh_repo_url():
    errors = env_settings.validate_fields({"REPO_URL": "git@github.com:sscarw/autodev-demo-target.git"})
    assert "REPO_URL" not in errors
