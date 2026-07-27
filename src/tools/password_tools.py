"""Password reset request tools for agents."""

from src.auth_config import USERS
from src.storage.password_reset_store import PasswordResetStore

# Module-level store instance (shared across all tool calls)
password_reset_store = PasswordResetStore("data/password_reset_requests.json")


def reset_password_tool(user_email: str) -> dict:
    """
    Raise a password reset request for a user. Does not change the actual
    password — the request is queued for IT to fulfill, same as a ticket.

    Args:
        user_email: Email of the user requesting the password reset

    Returns:
        dict with keys:
            - status: "success" or "error"
            - request_id: ID of the created request (if success)
            - message: Human-readable confirmation message
    """
    if user_email not in USERS:
        return {
            "status": "error",
            "message": f"User {user_email} not found.",
        }

    request = password_reset_store.create_request(user_email)
    return {
        "status": "success",
        "request_id": request.id,
        "message": f"Password reset request {request.id} raised for {user_email}. IT will process it shortly.",
    }


def list_pending_password_reset_requests_tool() -> dict:
    """
    List all pending password reset requests (admin tool).

    Returns:
        dict with keys: status, requests (list of dicts with request_id, user_email, requested_at)
    """
    requests = password_reset_store.list_pending_requests()
    return {
        "status": "success",
        "requests": [
            {
                "request_id": r.id,
                "user_email": r.user_email,
                "requested_at": r.requested_at,
            }
            for r in requests
        ],
    }
