#!/usr/bin/env python
"""Demo script to show session auto-save behavior."""

import sys
from src.sessions import (
    create_session,
    get_session,
    list_sessions,
    update_session,
    delete_session,
    SESSIONS_FILE,
)

# Clean up before demo
if SESSIONS_FILE.exists():
    SESSIONS_FILE.unlink()
    print("[OK] Cleaned previous sessions\n")

# Simulate user asking a question
print("[1] User asks: 'How do I reset my password?'")
messages_1 = [{"role": "user", "content": "How do I reset my password?"}]
session_id_1 = create_session("employee", messages_1)
print(f"    -> Auto-created session: {session_id_1}")
print(f"    -> Session name: '{get_session(session_id_1)['name']}'\n")

# Simulate AI response
print("[2] AI responds: 'To reset your password...'")
messages_1.append(
    {"role": "assistant", "content": "To reset your password, click on 'Forgot Password' on the login page..."}
)
update_session(session_id_1, messages_1)
print("    -> Auto-saved to session\n")

# Simulate another conversation
print("[3] User starts new conversation: 'What is VPN?'")
messages_2 = [{"role": "user", "content": "What is VPN?"}]
session_id_2 = create_session("engineer", messages_2)
print(f"    -> Auto-created new session: {session_id_2}")
print(f"    -> Session name: '{get_session(session_id_2)['name']}'\n")

# Show session history
print("[4] Session History (sorted by recency):")
sessions = list_sessions()
for idx, (sid, session_data) in enumerate(sessions, 1):
    print(f"    {idx}. [{session_data['role']}] {session_data['name'][:40]}")
    print(f"       Messages: {len(session_data['messages'])}")
print()

# Load and continue a session
print("[5] User clicks to load first session")
loaded = get_session(session_id_1)
print(f"    -> Loaded: '{loaded['name']}'")
print(f"    -> Messages in conversation: {len(loaded['messages'])}\n")

# Add more to loaded session
print("[6] User continues: 'But I don't see that button'")
loaded["messages"].append(
    {"role": "user", "content": "But I don't see that button"}
)
update_session(session_id_1, loaded["messages"])
print("    -> Auto-saved continuation\n")

# Show final state
print("[7] Final Session List:")
sessions = list_sessions()
for idx, (sid, session_data) in enumerate(sessions, 1):
    print(f"    {idx}. [{session_data['role']}] {session_data['name'][:40]}")
    print(f"       Messages: {len(session_data['messages'])} | Updated: {session_data['updated_at'][:10]}")

print("\n[SUCCESS] Demo complete! Sessions saved to data/sessions.json")
print("          In the Streamlit app:")
print("          - Sessions auto-create when user sends first message")
print("          - Names auto-generate from user's first message")
print("          - Sessions auto-save after each AI response")
print("          - Click 'Load' to restore a session")
print("          - Click 'Delete' to remove a session")
