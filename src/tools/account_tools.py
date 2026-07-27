"""Account unlock tool for agents (admin only)."""

from src.auth_config import USERS, get_account_status, set_account_status


def unlock_account_tool(user_email: str) -> dict:
    """
    Unlock a user's account so they can log in again.

    Args:
        user_email: Email of the user whose account to unlock

    Returns:
        dict with keys:
            - status: "success" or "error"
            - message: Human-readable confirmation message
    """
    if user_email not in USERS:
        return {
            "status": "error",
            "message": f"User {user_email} not found.",
        }

    if get_account_status(user_email) != "locked":
        return {
            "status": "error",
            "message": f"Account {user_email} is not locked.",
        }

    set_account_status(user_email, "unlocked")
    return {
        "status": "success",
        "message": f"Account {user_email} has been unlocked.",
    }
