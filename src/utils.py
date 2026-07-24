"""Utility functions for message handling and formatting."""


def format_message(role: str, content: str) -> dict:
    """Format a message into standard dict format.

    Args:
        role: "user" or "assistant"
        content: Message text

    Returns:
        Formatted message dict
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

    if not content or not content.strip():
        raise ValueError("Message content cannot be empty")

    return {
        "role": role,
        "content": content.strip()
    }


def get_recent_messages(history: list[dict], window: int = 10) -> list[dict]:
    """Get the most recent N messages from history.

    Args:
        history: Full conversation history
        window: Number of recent messages to return

    Returns:
        List of most recent messages (up to window size)
    """
    if window <= 0:
        raise ValueError("Window must be positive")

    return history[-window:] if len(history) > window else history
