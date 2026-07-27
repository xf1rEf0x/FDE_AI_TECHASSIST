"""Password reset tools for agents."""

import json
import os
import string
import secrets
from datetime import datetime
from src.auth_config import USERS

# Password storage file for audit trail
PASSWORD_LOG_FILE = "data/passwords.json"


def _load_password_log() -> dict:
    """Load password log from JSON file."""
    if not os.path.exists(PASSWORD_LOG_FILE):
        return {"resets": []}
    try:
        with open(PASSWORD_LOG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"resets": []}


def _save_password_log(log: dict) -> None:
    """Save password log to JSON file."""
    os.makedirs(os.path.dirname(PASSWORD_LOG_FILE), exist_ok=True)
    with open(PASSWORD_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def _generate_temporary_password(length: int = 12) -> str:
    """
    Generate a random temporary password.

    Args:
        length: Length of password (default 12)

    Returns:
        Random alphanumeric password
    """
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def reset_password_tool(user_email: str) -> dict:
    """
    Reset a user's password and return temporary password.

    Args:
        user_email: Email of the user requesting password reset

    Returns:
        dict with keys:
            - status: "success" or "error"
            - new_password: The generated temporary password (if success)
            - message: Human-readable confirmation message
    """
    if user_email not in USERS:
        return {
            "status": "error",
            "message": f"User {user_email} not found.",
        }

    new_password = _generate_temporary_password()
    USERS[user_email]["password"] = new_password

    # Log the reset for audit trail
    log = _load_password_log()
    log["resets"].append({
        "user_email": user_email,
        "timestamp": datetime.now().isoformat(),
        "password": new_password,
    })
    _save_password_log(log)

    return {
        "status": "success",
        "new_password": new_password,
        "message": f"Password reset successfully for {user_email}. New temporary password has been generated.",
    }
