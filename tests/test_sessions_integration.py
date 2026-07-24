"""Integration tests for session auto-save flow."""

import pytest
from src.sessions import create_session, get_session, list_sessions, SESSIONS_FILE


@pytest.fixture
def clean_sessions():
    """Clean sessions file before and after each test."""
    if SESSIONS_FILE.exists():
        SESSIONS_FILE.unlink()
    yield
    if SESSIONS_FILE.exists():
        SESSIONS_FILE.unlink()


def test_auto_save_flow_on_first_user_message(clean_sessions):
    """Test that a session is created with just the user message."""
    messages = [
        {"role": "user", "content": "How do I reset my password?"}
    ]
    session_id = create_session("employee", messages)

    # Verify session was created and named after user message
    session = get_session(session_id)
    assert session is not None
    assert session["name"] == "How do I reset my password?"
    assert len(session["messages"]) == 1


def test_auto_save_flow_with_assistant_response(clean_sessions):
    """Test that a session is updated with assistant response."""
    messages = [
        {"role": "user", "content": "How do I reset my password?"}
    ]
    session_id = create_session("employee", messages)

    # Simulate adding assistant response
    messages.append(
        {"role": "assistant", "content": "To reset your password, go to..."}
    )

    # Update the session
    from src.sessions import update_session
    update_session(session_id, messages)

    # Verify both messages are in session
    session = get_session(session_id)
    assert len(session["messages"]) == 2
    assert session["messages"][0]["role"] == "user"
    assert session["messages"][1]["role"] == "assistant"


def test_multi_turn_conversation_auto_saved(clean_sessions):
    """Test that multi-turn conversation auto-saves correctly."""
    from src.sessions import update_session

    messages = [
        {"role": "user", "content": "What is VPN?"}
    ]
    session_id = create_session("engineer", messages)

    # Simulate multi-turn conversation
    messages.append({"role": "assistant", "content": "VPN is a virtual private network that..."})
    update_session(session_id, messages)

    messages.append({"role": "user", "content": "How do I connect to the company VPN?"})
    update_session(session_id, messages)

    messages.append({"role": "assistant", "content": "To connect, follow these steps..."})
    update_session(session_id, messages)

    # Verify all turns are saved
    session = get_session(session_id)
    assert len(session["messages"]) == 4
    assert session["messages"][-1]["role"] == "assistant"


def test_session_loaded_and_continued(clean_sessions):
    """Test that a loaded session can be continued with new messages."""
    from src.sessions import update_session

    # Create initial session
    messages = [
        {"role": "user", "content": "How do I update my software?"},
        {"role": "assistant", "content": "To update, go to Settings..."}
    ]
    session_id = create_session("employee", messages)

    # Load the session (simulating user clicking to restore)
    loaded_session = get_session(session_id)
    loaded_messages = loaded_session["messages"].copy()

    # Continue the conversation
    loaded_messages.append({"role": "user", "content": "Where is Settings located?"})
    update_session(session_id, loaded_messages)

    # Verify new message was added to the saved session
    final_session = get_session(session_id)
    assert len(final_session["messages"]) == 3
    assert final_session["messages"][-1]["content"] == "Where is Settings located?"


def test_sessions_ordered_by_recency(clean_sessions):
    """Test that list_sessions returns most recently updated session first."""
    from src.sessions import update_session

    # Create first session
    session_1 = create_session("employee", [{"role": "user", "content": "Q1"}])

    # Create second session
    session_2 = create_session("engineer", [{"role": "user", "content": "Q2"}])

    # Update first session to make it more recent
    update_session(session_1, [
        {"role": "user", "content": "Q1"},
        {"role": "assistant", "content": "A1"}
    ])

    # List sessions - session_1 should be first (most recent)
    sessions = list_sessions()
    assert len(sessions) == 2
    assert sessions[0][0] == session_1
    assert sessions[1][0] == session_2
