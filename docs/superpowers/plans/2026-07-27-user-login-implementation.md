# User Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user login to the TechAssist AI app so users only see their own data (admin sees all).

**Architecture:** Login form at app startup; valid credentials stored in session state. Asset filtering applied in asset_agent and employee_service based on logged-in user's ID.

**Tech Stack:** Streamlit, Python, JSON (employee_assets.json as user source)

## Global Constraints

- Demo app — prioritize simplicity over production patterns
- Hardcoded users only; no registration
- Admin role sees all employee data; employee role sees only their own
- Session state persists within browser session (clears on close)

---

### Task 1: Create auth_config.py with hardcoded users

**Files:**
- Create: `src/auth_config.py`

**Interfaces:**
- Produces: `USERS` dict with keys = email, values = {password, employee_id, name, role}

- [ ] **Step 1: Extract employee names and IDs from employee_assets.json**

From the data file, the employees are:
- Alice Johnson (EMP001)
- Bob Smith (EMP002)
- Carol Davis (EMP003)
- David Wilson (EMP004)

Plus one admin user.

- [ ] **Step 2: Create src/auth_config.py**

```python
"""Hardcoded user credentials for demo app."""

USERS = {
    "alice@techassist.com": {
        "password": "password123",
        "employee_id": "EMP001",
        "name": "Alice Johnson",
        "role": "employee"
    },
    "bob@techassist.com": {
        "password": "password123",
        "employee_id": "EMP002",
        "name": "Bob Smith",
        "role": "employee"
    },
    "carol@techassist.com": {
        "password": "password123",
        "employee_id": "EMP003",
        "name": "Carol Davis",
        "role": "employee"
    },
    "david@techassist.com": {
        "password": "password123",
        "employee_id": "EMP004",
        "name": "David Wilson",
        "role": "employee"
    },
    "admin@techassist.com": {
        "password": "admin123",
        "employee_id": None,
        "name": "Admin User",
        "role": "admin"
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add src/auth_config.py
git commit -m "feat: add hardcoded user credentials"
```

---

### Task 2: Create auth.py with login/logout functions

**Files:**
- Create: `src/auth.py`

**Interfaces:**
- Consumes: `src/auth_config.py` → `USERS`
- Produces:
  - `login(email: str, password: str) -> dict | None` — returns user dict or None if invalid
  - `logout() -> None` — clears session state
  - `get_current_user() -> dict | None` — returns logged-in user or None
  - `is_admin() -> bool` — checks if current user is admin

- [ ] **Step 1: Create src/auth.py**

```python
"""Authentication helpers for demo app."""

import streamlit as st
from src.auth_config import USERS


def login(email: str, password: str) -> dict | None:
    """
    Validate email/password against hardcoded users.
    Returns user dict if valid, None otherwise.
    """
    if email not in USERS:
        return None
    
    user = USERS[email]
    if user["password"] != password:
        return None
    
    # Store in session state
    st.session_state.user = {
        "email": email,
        "employee_id": user["employee_id"],
        "name": user["name"],
        "role": user["role"]
    }
    return st.session_state.user


def logout() -> None:
    """Clear login session."""
    if "user" in st.session_state:
        del st.session_state.user
    st.rerun()


def get_current_user() -> dict | None:
    """Get currently logged-in user or None."""
    return st.session_state.get("user")


def is_admin() -> bool:
    """Check if current user is admin."""
    user = get_current_user()
    return user is not None and user.get("role") == "admin"
```

- [ ] **Step 2: Commit**

```bash
git add src/auth.py
git commit -m "feat: add authentication helpers"
```

---

### Task 3: Modify app.py to add login gate and logout button

**Files:**
- Modify: `app.py` (top section and sidebar)

**Interfaces:**
- Consumes: `src/auth.py` → `login()`, `logout()`, `get_current_user()`

- [ ] **Step 1: Add login check at the very top of app.py (after imports, before page config)**

Replace the current `st.set_page_config()` block with:

```python
"""TechAssist AI Phase 1: Streamlit chatbot with role-based personas."""

import os
import streamlit as st
from src.conversation import get_response, get_response_stream
from src.prompts import get_available_roles, get_system_prompt, get_prompt_templates
from src.utils import format_message
from src.sessions import (
    create_session,
    get_session,
    delete_session,
    list_sessions,
    update_session,
)
from src.employee_service import (
    render_employee_assets,
    render_helpdesk,
    render_software_request,
    render_user_account,
)
from src.auth import login, logout, get_current_user, is_admin

# ============================================================================
# LOGIN GATE
# ============================================================================

st.set_page_config(
    page_title="TechAssist AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check if user is logged in
if not get_current_user():
    st.title("🔐 TechAssist AI Login")
    st.markdown("*Secure IT Support Assistant for TechAssist Solutions*")
    
    with st.form("login_form"):
        email = st.text_input("Email:", placeholder="e.g., alice@techassist.com")
        password = st.text_input("Password:", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if not email or not password:
                st.error("Please enter email and password.")
            else:
                user = login(email, password)
                if user:
                    st.success(f"Welcome, {user['name']}!")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
    
    # Demo credentials hint
    st.info("""
    **Demo credentials:**
    - alice@techassist.com / password123
    - bob@techassist.com / password123
    - carol@techassist.com / password123
    - david@techassist.com / password123
    - admin@techassist.com / admin123
    """)
    st.stop()

# ============================================================================
# MAIN APP (user is logged in)
# ============================================================================

st.title("🤖 TechAssist AI Support Assistant")
st.markdown("*Your friendly IT support assistant for TechAssist Solutions*")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "role" not in st.session_state:
    st.session_state.role = "employee"


if "template_selected" not in st.session_state:
    st.session_state.template_selected = None

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7

# Sidebar: Role and model selector
with st.sidebar:
    st.header("Settings")
    
    # Current user info and logout
    current_user = get_current_user()
    if current_user:
        st.markdown(f"**Logged in as:** {current_user['name']}")
        st.markdown(f"**Role:** {current_user['role'].capitalize()}")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
    
    st.divider()

    available_roles = get_available_roles()
    selected_role = st.selectbox(
        "Select your role:",
        available_roles,
        index=available_roles.index(st.session_state.role),
        help="Choose your role to get personalized IT support"
    )

    # Update role and clear history if changed
    if selected_role != st.session_state.role:
        st.session_state.role = selected_role
        st.session_state.messages = []
        st.info(f"✓ Switched to {selected_role} role. Chat history cleared.")

    st.info("🤖 Using HuggingFace model: DeepSeek-R1")

    # Temperature slider
    st.session_state.temperature = st.slider(
        "Temperature:",
        min_value=0.0,
        max_value=2.0,
        value=st.session_state.temperature,
        step=0.1,
        help="Lower = more focused/deterministic, Higher = more creative/random"
    )

    # Show current role info
    with st.expander("ℹ️ About your role"):
        st.markdown(get_system_prompt(st.session_state.role))

    st.divider()

    # Session history section
    st.subheader("📋 Session History")

    # List saved sessions
    sessions = list_sessions()
    if sessions:
        for session_id, session_data in sessions:
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(
                    f"🔄 {session_data['name'][:40]}",
                    use_container_width=True,
                    key=f"load_{session_id}"
                ):
                    loaded = get_session(session_id)
                    if loaded:
                        st.session_state.messages = loaded["messages"]
                        st.session_state.role = loaded["role"]
                        st.session_state.current_session_id = session_id
                        st.success(f"✓ Loaded: {loaded['name']}")
                        st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{session_id}", help="Delete session"):
                    delete_session(session_id)
                    if st.session_state.current_session_id == session_id:
                        st.session_state.current_session_id = None
                        st.session_state.messages = []
                    st.success("Deleted")
                    st.rerun()
        st.caption(f"Total: {len(sessions)} session(s)")
    else:
        st.caption("💬 Start a conversation to create a session")

    st.divider()

    # Clear conversation button
    if st.button("New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.template_selected = None
        st.session_state.current_session_id = None
        st.success("Conversation cleared!")
        st.rerun()

# Main content tabs
tab_chat, tab_assets, tab_helpdesk, tab_software, tab_account = st.tabs([
    "💬 AI Chat",
    "🏢 Employee Assets",
    "🎫 HelpDesk",
    "💾 Software Request",
    "👤 User Account"
])

with tab_chat:
    # Display conversation history
    st.subheader("Conversation")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    user_input = st.chat_input("Ask me anything about IT support...")

    # Prompt templates below chat input
    if not st.session_state.messages:
        st.markdown("**Quick questions for your role:**")
        templates = get_prompt_templates(st.session_state.role)
        cols = st.columns(len(templates))
        for idx, template in enumerate(templates):
            with cols[idx]:
                if st.button(template, use_container_width=True, key=f"template_{idx}_{template[:10]}"):
                    st.session_state.template_selected = template
                    st.rerun()

    # Handle template selection
    if st.session_state.template_selected and not st.session_state.messages:
        user_input = st.session_state.template_selected
        st.session_state.template_selected = None

    if user_input:
        # Validate input
        if not user_input.strip():
            st.warning("Please enter a message.")
            st.stop()

        # Add user message to history
        user_message = format_message("user", user_input)
        st.session_state.messages.append(user_message)

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get and display assistant response
        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()

                # Show thinking animation
                message_placeholder.markdown("🤔 *Thinking...*")

                full_response = ""

                # Use streaming to display response in real-time
                for chunk in get_response_stream(user_input, st.session_state.role, st.session_state.messages[:-1], temperature=st.session_state.temperature):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")

                # Final response without cursor
                message_placeholder.markdown(full_response)

            # Add assistant message to history
            assistant_message = format_message("assistant", full_response)
            st.session_state.messages.append(assistant_message)

            # Auto-create session on first response if not already in a session
            if not st.session_state.current_session_id:
                st.session_state.current_session_id = create_session(st.session_state.role, st.session_state.messages)

            # Auto-save current session
            if st.session_state.current_session_id:
                update_session(st.session_state.current_session_id, st.session_state.messages)
                st.rerun()

        except ValueError as e:
            st.error(f"❌ {e}")
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ Error: {error_msg}")
            if "API" in error_msg or "key" in error_msg.lower():
                st.info("Please check your HuggingFace API key in `.env` and try again.")

with tab_assets:
    render_employee_assets()

with tab_helpdesk:
    render_helpdesk()

with tab_software:
    render_software_request()

with tab_account:
    render_user_account()
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: add login gate and logout button"
```

---

### Task 4: Modify asset_agent.py to filter by user_id

**Files:**
- Modify: `src/asset_agent.py`

**Interfaces:**
- Consumes: User ID (passed from employee_service)
- Produces: `search_assets()` now filters results by employee_id

- [ ] **Step 1: Update search_assets() to accept and use user_id**

Find the `search_assets()` function signature and update it:

```python
def search_assets(
    query: str,
    chat_history: list = None,
    temperature: float = 0.7,
    user_name: str = None,
    user_id: str = None,  # NEW PARAMETER
    is_admin: bool = False  # NEW PARAMETER
) -> str:
```

Then update the asset filtering logic. Find where assets are loaded from JSON and add this filter:

```python
    # Load employee assets
    with open("data/employee_assets.json", "r") as f:
        data = json.load(f)
    
    # Filter employees by user access level
    employees = data.get("employees", [])
    
    # If not admin, only show current user's assets
    if not is_admin and user_id:
        employees = [emp for emp in employees if emp.get("employee_id") == user_id]
    
    # Rest of the search logic uses the filtered employees list
```

- [ ] **Step 2: Commit**

```bash
git add src/asset_agent.py
git commit -m "feat: add user_id filtering to asset search"
```

---

### Task 5: Modify employee_service.py to pass user_id to asset_agent

**Files:**
- Modify: `src/employee_service.py` (render_employee_assets function)

**Interfaces:**
- Consumes: `src/auth.py` → `get_current_user()`, `is_admin()`
- Produces: Passes user_id and is_admin to search_assets()

- [ ] **Step 1: Add imports at top of employee_service.py**

```python
from src.auth import get_current_user, is_admin
```

- [ ] **Step 2: Update render_employee_assets() to filter**

Find the `render_employee_assets()` function and update it to pass user_id and is_admin:

```python
def render_employee_assets():
    """Render Employee Assets service tab with AI Agent-powered search."""
    st.subheader("🏢 Employee Assets")
    
    # Get current user info
    current_user = get_current_user()
    if not current_user:
        st.warning("Please login to view assets.")
        return
    
    user_id = current_user.get("employee_id")
    user_admin = is_admin()
    
    st.markdown("Search for your assigned assets using natural language. Ask about laptops, monitors, software licenses, printers, or anything else.")

    # Initialize chat history for this session
    if "asset_chat_history" not in st.session_state:
        st.session_state.asset_chat_history = []

    if "asset_search_temperature" not in st.session_state:
        st.session_state.asset_search_temperature = 0.7

    # Display chat history
    st.markdown("### Asset Search Conversation")
    for message in st.session_state.asset_chat_history:
        role = message["role"]
        content = message["content"]
        with st.chat_message(role):
            st.markdown(content)

    # User input
    user_query = st.chat_input("Ask about your assets (e.g., 'Show me my laptop', 'Find my Microsoft Office license')...")

    if user_query:
        # Add user message to history
        st.session_state.asset_chat_history.append({
            "role": "user",
            "content": user_query
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)

        # Get agent response
        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🤔 *Searching assets...*")

                # Call asset search agent with user_id and admin flag
                response = search_assets(
                    user_query,
                    chat_history=st.session_state.asset_chat_history[:-1],
                    temperature=st.session_state.asset_search_temperature,
                    user_name=current_user.get("name"),
                    user_id=user_id,  # NEW
                    is_admin=user_admin  # NEW
                )

                message_placeholder.markdown(response)

            # Add assistant message to history
            st.session_state.asset_chat_history.append({
                "role": "assistant",
                "content": response
            })

        except Exception as e:
            st.error(f"❌ Error searching assets: {str(e)}")

    # Optional: User identification (for "me" queries)
    with st.expander("👤 Your Info"):
        st.markdown(f"**Name:** {current_user.get('name')}")
        st.markdown(f"**Employee ID:** {user_id}")
        st.markdown(f"**Role:** {current_user.get('role').capitalize()}")

    # Sidebar controls
    with st.sidebar:
        if st.button("Clear Asset Search History"):
            st.session_state.asset_chat_history = []
            st.success("Asset search history cleared!")
            st.rerun()
```

- [ ] **Step 2: Commit**

```bash
git add src/employee_service.py
git commit -m "feat: pass user_id to asset search for filtering"
```

---

### Task 6: Test login flow end-to-end

**Files:**
- Test: Manual testing in browser

- [ ] **Step 1: Start the Streamlit app**

```bash
streamlit run app.py
```

- [ ] **Step 2: Verify login page appears**

Expected: Login form with email and password fields, demo credentials hint below.

- [ ] **Step 3: Test invalid credentials**

- Try email that doesn't exist → Error message
- Try wrong password → Error message

- [ ] **Step 4: Test valid employee login**

- Login as alice@techassist.com / password123
- Expected: Redirects to app, shows "Logged in as: Alice Johnson" in sidebar
- Go to "Employee Assets" tab
- Search for assets (e.g., "Show my laptop")
- Verify only Alice's assets appear (MacBook Pro, Dell Monitor, IntelliJ license)
- Logout button should clear session

- [ ] **Step 5: Test admin login**

- Login as admin@techassist.com / admin123
- Go to "Employee Assets" tab
- Search for "laptops"
- Verify ALL employees' laptops appear (MacBook Pro, Dell XPS, ThinkPad, MacBook Air)

- [ ] **Step 6: Test session persistence**

- Login as bob@techassist.com
- Refresh page (Ctrl+R)
- Expected: Still logged in (session persists)
- Close browser tab and reopen app
- Expected: Back at login screen (session cleared)

- [ ] **Step 7: Commit test notes**

```bash
git commit -m "test: verify login flow, data filtering, and session persistence"
```

---

## Self-Review

✅ **Spec coverage:**
- Login page (Task 3)
- Hardcoded users from employee_assets.json (Task 1)
- Admin sees all, employees see own data (Tasks 4–5, tested in Task 6)
- Simple, demo-focused implementation (all tasks)

✅ **Placeholder scan:** No TBD, TODO, or vague steps.

✅ **Type consistency:** All function signatures match across tasks.
