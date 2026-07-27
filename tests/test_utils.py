"""Unit tests for utility functions."""

import pytest
from src.utils import format_message


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
