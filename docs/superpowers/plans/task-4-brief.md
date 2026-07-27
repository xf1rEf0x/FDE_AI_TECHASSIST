# Task 4: Integrate Help Desk Agent into Streamlit UI

**Location:** Fourth task of Help Desk Agent implementation plan.
**Purpose:** Add Help Desk tab to Streamlit app with chat interface for ticket operations.

## Requirements

Modify/Create:
- `src/ui/helpdesk_tab.py` - New UI module (tab rendering logic)
- `app.py` - Modify existing app to add Help Desk tab

### Dependencies

This task depends on Task 3:
- Import `HelpDeskAgent` from `src.agents.helpdesk_agent`

### `src/ui/helpdesk_tab.py` — New Module

Create a function:

```python
def render_helpdesk_tab(user_email: str):
    """Render the Help Desk tab with ticket creation and status checking."""
```

**Behavior:**
1. Display header: "Help Desk"
2. Initialize agent on first tab visit: `st.session_state.helpdesk_agent = HelpDeskAgent(user_email)`
3. Initialize message history: `st.session_state.helpdesk_messages = []`
4. Display chat history from session state (loop through messages, use st.chat_message())
5. Render chat input: `st.chat_input("Ask about creating or checking a ticket...")`
6. On user input:
   - Append user message to history
   - Display user message with st.chat_message("user")
   - Run agent: `response = st.session_state.helpdesk_agent.run(user_input)`
   - Display assistant response with st.chat_message("assistant")
   - Append assistant response to history

**Session State Keys:**
- `helpdesk_agent` — HelpDeskAgent instance (created once per session)
- `helpdesk_messages` — List of dicts with keys: role (user/assistant), content (string)

### Modify `app.py`

Find the existing tab structure in the main app function. It likely looks like:
```python
tab1, tab2 = st.tabs(["Chat", "Asset Agent"])
with tab1:
    ...
with tab2:
    ...
```

**Changes:**
1. Import the new module: `from src.ui.helpdesk_tab import render_helpdesk_tab`
2. Update tabs to three: `tab1, tab2, tab3 = st.tabs(["Chat", "Asset Agent", "Help Desk"])`
3. Add Help Desk tab rendering:
```python
with tab3:
    render_helpdesk_tab(user_email)
```

(The user_email variable should already be available in the app context from existing code.)

### Global Constraints

- Use existing Streamlit patterns (st.session_state, st.chat_message, st.chat_input)
- No new dependencies
- Reuse session state pattern from existing tabs (if Chat tab uses st.session_state, follow same pattern)
- Agent is instantiated once per session (not on every render)

### Testing

**Manual testing in Streamlit UI:**

```
# Prerequisites:
streamlit run app.py

# Test workflow:
1. Login or navigate past role/email selection
2. Click "Help Desk" tab
3. Type: "Create a ticket for my laptop not starting"
4. Verify: Agent response appears, contains ticket ID
5. Type: "Check the status of ticket {TICKET_ID}"
6. Verify: Agent returns ticket details
7. Refresh page
8. Click "Help Desk" tab again
9. Verify: Chat history persists (messages still visible)
```

### Implementation Notes

- The agent.run() method already returns a string (no parsing needed)
- Session state is Streamlit-native (survives reruns, not persisted to disk)
- The agent enforces access control (user_email is passed to HelpDeskAgent), so no guards needed in the UI
- If user switches to a different tab and back, the agent instance is still in session_state (efficient)
