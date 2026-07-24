"""Tests for session history persistence."""

import pytest
import json
from pathlib import Path
from src.sessions import (
    create_session,
    get_session,
    delete_session,
    list_sessions,
    update_session,
    load_sessions,
    save_sessions,
    SESSIONS_FILE,
)


@pytest.fixture
def clean_sessions():
    """Clean sessions file before and after each test."""
    if SESSIONS_FILE.exists():
        SESSIONS_FILE.unlink()
    yield
    if SESSIONS_FILE.exists():
        SESSIONS_FILE.unlink()


def test_create_session_auto_names_from_first_user_message(clean_sessions):
    """Test that session name is auto-generated from first user message."""
    messages = [
        {"role": "user", "content": "How do I reset my password?"},
        {"role": "assistant", "content": "Here's how..."}
    ]
    session_id = create_session("employee", messages)

    session = get_session(session_id)
    assert session is not None
    assert session["name"] == "How do I reset my password?"
    assert session["role"] == "employee"
    assert session["messages"] == messages


def test_create_session_truncates_long_messages(clean_sessions):
    """Test that long first messages are truncated."""
    long_msg = "x" * 100
    messages = [
        {"role": "user", "content": long_msg},
        {"role": "assistant", "content": "Response"}
    ]
    session_id = create_session("engineer", messages)

    session = get_session(session_id)
    assert len(session["name"]) <= 53  # 50 chars + "..."


def test_create_session_default_name_when_no_user_message(clean_sessions):
    """Test that default name is used when no user message exists."""
    messages = [{"role": "assistant", "content": "Response"}]
    session_id = create_session("admin", messages)

    session = get_session(session_id)
    assert session["name"] == "New Conversation"


def test_get_session_returns_none_for_nonexistent_id(clean_sessions):
    """Test that get_session returns None for invalid session ID."""
    assert get_session("nonexistent") is None


def test_update_session_preserves_messages(clean_sessions):
    """Test that update_session updates messages and timestamp."""
    messages = [
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Answer 1"}
    ]
    session_id = create_session("employee", messages)
    original_created = get_session(session_id)["created_at"]

    new_messages = messages + [
        {"role": "user", "content": "Question 2"},
        {"role": "assistant", "content": "Answer 2"}
    ]
    update_session(session_id, new_messages)

    updated = get_session(session_id)
    assert updated["messages"] == new_messages
    assert updated["created_at"] == original_created
    assert updated["updated_at"] > original_created


def test_delete_session(clean_sessions):
    """Test that delete_session removes a session."""
    messages = [{"role": "user", "content": "Test"}]
    session_id = create_session("employee", messages)

    assert get_session(session_id) is not None
    delete_session(session_id)
    assert get_session(session_id) is None


def test_delete_nonexistent_session_does_not_raise(clean_sessions):
    """Test that deleting a nonexistent session doesn't raise."""
    delete_session("nonexistent")  # Should not raise


def test_list_sessions_sorted_by_update_time(clean_sessions):
    """Test that list_sessions returns sessions sorted by update time (newest first)."""
    session_id_1 = create_session("employee", [{"role": "user", "content": "First"}])
    session_id_2 = create_session("engineer", [{"role": "user", "content": "Second"}])

    sessions = list_sessions()
    assert len(sessions) == 2
    assert sessions[0][0] == session_id_2  # Newer first
    assert sessions[1][0] == session_id_1


def test_list_sessions_empty_when_no_sessions(clean_sessions):
    """Test that list_sessions returns empty list when no sessions exist."""
    sessions = list_sessions()
    assert sessions == []


def test_load_and_save_sessions(clean_sessions):
    """Test that load_sessions and save_sessions work correctly."""
    test_data = {
        "session_1": {
            "name": "Test Session",
            "role": "employee",
            "messages": [],
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        }
    }

    save_sessions(test_data)
    loaded = load_sessions()
    assert loaded == test_data


def test_session_has_timestamps(clean_sessions):
    """Test that created session has created_at and updated_at timestamps."""
    messages = [{"role": "user", "content": "Test"}]
    session_id = create_session("employee", messages)

    session = get_session(session_id)
    assert "created_at" in session
    assert "updated_at" in session
    # Both should be set, may differ by microseconds
    assert session["created_at"] is not None
    assert session["updated_at"] is not None


def test_multiple_sessions_independent(clean_sessions):
    """Test that multiple sessions are independent."""
    session_1 = create_session("employee", [{"role": "user", "content": "Q1"}])
    session_2 = create_session("engineer", [{"role": "user", "content": "Q2"}])

    update_session(session_1, [{"role": "user", "content": "Q1"}, {"role": "assistant", "content": "A1"}])

    s1 = get_session(session_1)
    s2 = get_session(session_2)

    assert len(s1["messages"]) == 2
    assert len(s2["messages"]) == 1
