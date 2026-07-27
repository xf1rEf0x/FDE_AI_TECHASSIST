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

    return {"role": role, "content": content.strip()}
