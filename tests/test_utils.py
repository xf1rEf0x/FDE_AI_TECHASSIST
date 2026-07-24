"""Unit tests for utility functions."""

import pytest
from src.utils import format_message, get_recent_messages


def test_format_message_user():
    """Verify user message formatting."""
    msg = format_message("user", "Hello")
    assert msg["role"] == "user"
    assert msg["content"] == "Hello"


def test_format_message_assistant():
    """Verify assistant message formatting."""
    msg = format_message("assistant", "Hi there!")
    assert msg["role"] == "assistant"
    assert msg["content"] == "Hi there!"


def test_format_message_strips_whitespace():
    """Verify message content is stripped."""
    msg = format_message("user", "  Hello  ")
    assert msg["content"] == "Hello"


def test_format_message_invalid_role():
    """Verify invalid role raises error."""
    with pytest.raises(ValueError, match="Invalid role"):
        format_message("invalid", "Hello")


def test_format_message_empty_content():
    """Verify empty content raises error."""
    with pytest.raises(ValueError, match="cannot be empty"):
        format_message("user", "")


def test_format_message_whitespace_only():
    """Verify whitespace-only content raises error."""
    with pytest.raises(ValueError, match="cannot be empty"):
        format_message("user", "   ")


def test_get_recent_messages_full_history():
    """Verify getting recent messages from history smaller than window."""
    history = [
        {"role": "user", "content": "msg1"},
        {"role": "assistant", "content": "msg2"},
    ]
    recent = get_recent_messages(history, window=10)
    assert len(recent) == 2
    assert recent == history


def test_get_recent_messages_windowed():
    """Verify getting recent messages with window size."""
    history = [
        {"role": "user", "content": "msg1"},
        {"role": "assistant", "content": "msg2"},
        {"role": "user", "content": "msg3"},
        {"role": "assistant", "content": "msg4"},
    ]
    recent = get_recent_messages(history, window=2)
    assert len(recent) == 2
    assert recent == history[-2:]


def test_get_recent_messages_invalid_window():
    """Verify invalid window raises error."""
    with pytest.raises(ValueError, match="Window must be positive"):
        get_recent_messages([], window=0)
