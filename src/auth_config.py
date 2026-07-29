"""User credentials for demo app, loaded from data/users.json."""

import json
from pathlib import Path

from src.storage.blob_store import load_blob, save_blob

USERS_FILE = "data/users.json"


def _load_users() -> dict:
    """Load all user records. On Redis, seeds from the repo's checked-in
    data/users.json the first time (before any account_status changes have
    been saved to Redis), so login works out of the box on a fresh deploy."""
    seed = json.loads(Path(USERS_FILE).read_text()) if Path(USERS_FILE).exists() else {}
    return load_blob("users", USERS_FILE, seed)


def _save_users(users: dict) -> None:
    """Save all user records."""
    save_blob("users", USERS_FILE, users)


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
