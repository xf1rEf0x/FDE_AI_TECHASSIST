"""Session history persistence for chat conversations."""

import json
import uuid
from datetime import datetime
from pathlib import Path


SESSIONS_FILE = Path("data/sessions.json")


def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    SESSIONS_FILE.parent.mkdir(exist_ok=True)


def load_sessions() -> dict:
    """Load all sessions from file. Returns empty dict if file doesn't exist."""
    ensure_data_dir()
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_sessions(sessions: dict):
    """Write sessions to file."""
    ensure_data_dir()
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


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
