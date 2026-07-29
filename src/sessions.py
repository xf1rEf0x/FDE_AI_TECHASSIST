"""Session history persistence for chat conversations."""

import uuid
from datetime import datetime
from pathlib import Path

from src.storage.blob_store import load_blob, save_blob

SESSIONS_FILE = Path("data/sessions.json")


def load_sessions() -> dict:
    """Load all sessions. Returns empty dict if none exist yet."""
    return load_blob("sessions", SESSIONS_FILE, {})


def save_sessions(sessions: dict):
    """Save sessions."""
    save_blob("sessions", SESSIONS_FILE, sessions)


def create_session(role: str, messages: list) -> str:
    """Create a new session with auto-generated name from first user message. Returns session ID."""
    sessions = load_sessions()
    session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # Extract name from first user message
    name = "New Conversation"
    for msg in messages:
        if msg["role"] == "user":
            name = msg["content"][:50].strip()
            if len(msg["content"]) > 50:
                name += "..."
            break

    sessions[session_id] = {
        "name": name,
        "role": role,
        "messages": messages,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    save_sessions(sessions)
    return session_id


def get_session(session_id: str) -> dict | None:
    """Retrieve a session by ID."""
    sessions = load_sessions()
    return sessions.get(session_id)


def update_session(session_id: str, messages: list):
    """Update a session's messages and timestamp."""
    sessions = load_sessions()
    if session_id in sessions:
        sessions[session_id]["messages"] = messages
        sessions[session_id]["updated_at"] = datetime.now().isoformat()
        save_sessions(sessions)


def delete_session(session_id: str):
    """Delete a session by ID."""
    sessions = load_sessions()
    if session_id in sessions:
        del sessions[session_id]
        save_sessions(sessions)


def list_sessions() -> list[tuple[str, dict]]:
    """List all sessions sorted by update time (newest first). Returns list of (id, session) tuples."""
    sessions = load_sessions()
    return sorted(
        sessions.items(),
        key=lambda x: x[1].get("updated_at", ""),
        reverse=True
    )
