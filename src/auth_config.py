"""User credentials for demo app, loaded from data/users.json."""

import json
from pathlib import Path

USERS_FILE = Path("data/users.json")


def _load_users() -> dict:
    """Load all user records from disk."""
    with open(USERS_FILE) as f:
        return json.load(f)


def _save_users(users: dict) -> None:
    """Save all user records to disk."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


# Cached snapshot used for credential/profile lookups (password, employee_id,
# name, role). Only account_status is re-read from disk on every check, so
# editing that field in data/users.json directly (e.g. to unlock an account)
# takes effect without touching code.
USERS = _load_users()


def get_account_status(email: str) -> str | None:
    """Get the current account status for email, read fresh from disk."""
    user = _load_users().get(email)
    return user["account_status"] if user else None


def set_account_status(email: str, status: str) -> None:
    """Persist an account status change for email directly in data/users.json."""
    users = _load_users()
    if email in users:
        users[email]["account_status"] = status
        _save_users(users)
