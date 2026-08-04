"""Utility functions for message handling and formatting."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def get_build_info() -> str:
    """Read version.txt and commit.txt from the repo root for the UI footer."""
    version = (_ROOT / "version.txt").read_text().strip() if (_ROOT / "version.txt").exists() else "dev"
    commit = (_ROOT / "commit.txt").read_text().strip() if (_ROOT / "commit.txt").exists() else "unknown"
    return f"v{version} · {commit}"


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
