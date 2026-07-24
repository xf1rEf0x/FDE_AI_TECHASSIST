# Session History Feature

## Overview
Automatic session history with chat persistence in the left sidebar. Conversations are auto-created and auto-saved without any manual actions from the user.

## Features

### Auto-Create Sessions
- When a user sends their first message, a session is automatically created
- No manual "Save Session" button required
- Session ID: timestamp + 8-char UUID suffix (e.g., `20260724_150921_3b74423e`)

### Auto-Generated Names
- Session names are automatically extracted from the user's first message
- Long messages are truncated to 50 characters with "..." suffix
- Default name if no user message: "New Conversation"

### Auto-Save on Every Message
- After the AI responds, the entire conversation is automatically saved
- Loaded sessions update in real-time as users continue conversations
- Updated timestamps track the last change

### Left Sidebar Menu
Located under "Settings" → "📋 Session History":
- **Load Button (🔄)**: Click to restore a previous session
  - Loads all messages from that session
  - Switches to the session's role automatically
  - Session becomes "current" for auto-saving
- **Delete Button (🗑️)**: Click to permanently delete a session
- **Session List**: Sorted by recency (newest first)
  - Shows role badge: `[employee]`, `[engineer]`, `[admin]`
  - Shows session name (truncated to 40 chars)
  - Shows last updated date
- **Info**: "Total: N session(s)" or "Start a conversation to create a session"

## Data Storage

**File**: `data/sessions.json`

**Format**:
```json
{
  "SESSION_ID": {
    "name": "How do I reset my password?",
    "role": "employee",
    "messages": [
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ],
    "created_at": "2026-07-24T15:08:04.894724",
    "updated_at": "2026-07-24T15:09:21.457910"
  }
}
```

**Privacy**: Sessions file is in `.gitignore` (not committed to git)

## User Workflow

### Example 1: New Conversation
1. User types: "How do I reset my password?"
2. ✅ Session auto-created with name "How do I reset my password?"
3. AI responds: "To reset your password..."
4. ✅ Session auto-saved with both messages
5. Session now appears in left sidebar under "Session History"

### Example 2: Continue a Previous Conversation
1. User clicks "🔄 How do I reset my password?" in sidebar
2. ✅ Session loaded: all messages restored, role switched
3. User types: "But I don't see that button"
4. AI responds: "Try looking here..."
5. ✅ Session auto-updated with new messages
6. Session moves to top of list (sorted by recency)

### Example 3: Delete a Session
1. User clicks "🗑️" next to a session
2. ✅ Session permanently deleted
3. If it was the current session, chat clears
4. Session no longer appears in history

## Implementation Details

### Core Module: `src/sessions.py`
- `create_session(role, messages)` — Creates new session, auto-names from first user message
- `get_session(session_id)` — Retrieves a session by ID
- `update_session(session_id, messages)` — Updates messages and last-modified timestamp
- `delete_session(session_id)` — Permanently removes a session
- `list_sessions()` — Returns all sessions sorted by update time (newest first)
- `load_sessions()` / `save_sessions()` — Persistence layer

### App Integration: `app.py`
- Line 40-41: Initialize `st.session_state.current_session_id`
- Line 82-113: Sidebar session history UI
- Line 161-162: Auto-create session on first user message
- Line 191-192: Auto-save after AI response

## Testing

**Test Files**:
- `tests/test_sessions.py` — 12 unit tests (100% coverage of sessions module)
- `tests/test_sessions_integration.py` — 5 integration tests (auto-save flows)

**Test Coverage**:
- Auto-naming from first user message ✓
- Session creation and retrieval ✓
- Update and delete operations ✓
- List sorting by recency ✓
- Multi-turn conversation persistence ✓
- Load-and-continue workflows ✓

**All 55 Tests Pass** (38 existing + 17 new)

## Demo

Run the demo script to see session behavior:
```bash
python demo_sessions.py
```

Output shows:
- Auto-creation on first message
- Auto-save on AI response
- Session list sorted by recency
- Load and continue workflows
- Proper session data structure

## Notes

- **No database required** (Phase 1): Uses JSON for simplicity
- **Phase 4 upgrade path**: Migrate to persistent database when needed
- **Scale considerations**: Works for typical user counts; database upgrade in Phase 4 for enterprise scale
- **Privacy**: All sessions stored locally; suitable for on-premise deployment

## Files Changed/Added

| File | Change | Lines |
|------|--------|-------|
| `src/sessions.py` | NEW | 80 |
| `app.py` | Modified | 160 → 201 |
| `tests/test_sessions.py` | NEW | 165 |
| `tests/test_sessions_integration.py` | NEW | 98 |
| `.gitignore` | Modified | 20 → 21 |
| `demo_sessions.py` | NEW | 53 |
| **Total** | | **631 lines** |
