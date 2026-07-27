"""Utility functions for message handling and formatting."""


def format_message(role: str, content: str, metadata: dict = None) -> dict:
    """Format a message into standard dict format.

    Args:
        role: "user" or "assistant"
        content: Message text
        metadata: Optional dict with extra info (e.g. tools used, agent name)

    Returns:
        Formatted message dict
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

    if not content or not content.strip():
        raise ValueError("Message content cannot be empty")

    message = {"role": role, "content": content.strip()}
    if metadata:
        message["metadata"] = metadata
    return message
