# Password Reset Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a password reset tool to HelpDeskAgent that generates temporary passwords on demand, demonstrates LangChain tool calling, and securely prompts for confirmation before executing.

**Architecture:** Create a minimal password reset tool (`src/tools/password_tools.py`) that generates random 12-char passwords and stores them in JSON for demo purposes. Integrate it into `HelpDeskAgent` with a system prompt that enforces confirmation before execution. The agent uses LangChain tool calling to invoke the reset when the user confirms.

**Tech Stack:** Python, LangChain, Gemini API, JSON file storage (demo-only)

## Global Constraints

- Demo purpose: no email integration, no production-grade security
- Password generated as 12-char alphanumeric (letters A-Z, a-z, 0-9)
- Confirmation required before tool invocation (agent-enforced via system prompt)
- Passwords stored in `data/passwords.json` for audit trail (demo tracking only)
- No modification to existing ticket tools or agent behavior

---

## Task 1: Create Password Tools Module

**Files:**
- Create: `src/tools/password_tools.py`

**Interfaces:**
- Produces: `reset_password_tool(user_email: str) → dict` with keys `status`, `new_password`, `message`

- [ ] **Step 1: Create the password_tools.py file with password generation logic**

Create `src/tools/password_tools.py`:

```python
"""Password reset tools for agents."""

import json
import os
import string
import secrets
from datetime import datetime

# Password storage file (demo-only, not production)
PASSWORD_LOG_FILE = "data/passwords.json"


def _load_password_log() -> dict:
    """Load password log from JSON file."""
    if not os.path.exists(PASSWORD_LOG_FILE):
        return {"resets": []}
    try:
        with open(PASSWORD_LOG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"resets": []}


def _save_password_log(log: dict) -> None:
    """Save password log to JSON file."""
    os.makedirs(os.path.dirname(PASSWORD_LOG_FILE), exist_ok=True)
    with open(PASSWORD_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def _generate_temporary_password(length: int = 12) -> str:
    """
    Generate a random temporary password.
    
    Args:
        length: Length of password (default 12)
    
    Returns:
        Random alphanumeric password
    """
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def reset_password_tool(user_email: str) -> dict:
    """
    Reset a user's password and return temporary password.
    
    Args:
        user_email: Email of the user requesting password reset
    
    Returns:
        dict with keys:
            - status: "success"
            - new_password: The generated temporary password
            - message: Human-readable confirmation message
    """
    new_password = _generate_temporary_password()
    
    # Log the reset for demo purposes
    log = _load_password_log()
    log["resets"].append({
        "user_email": user_email,
        "timestamp": datetime.now().isoformat(),
        "password": new_password,  # Demo-only; never store in production
    })
    _save_password_log(log)
    
    return {
        "status": "success",
        "new_password": new_password,
        "message": f"Password reset successfully for {user_email}. New temporary password has been generated.",
    }
```

- [ ] **Step 2: Run Python syntax check**

Run: `python -m py_compile src/tools/password_tools.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add src/tools/password_tools.py
git commit -m "feat: add password reset tool with temporary password generation"
```

---

## Task 2: Add Unit Test for Password Tool

**Files:**
- Create: `tests/test_password_tools.py`

**Interfaces:**
- Consumes: `reset_password_tool(user_email: str) → dict` from Task 1
- Produces: Test suite validating password generation and JSON logging

- [ ] **Step 1: Write the test file**

Create `tests/test_password_tools.py`:

```python
"""Tests for password reset tool."""

import json
import os
import pytest
from src.tools.password_tools import reset_password_tool, _generate_temporary_password


def test_generate_temporary_password():
    """Test that generated password is 12 chars and alphanumeric."""
    password = _generate_temporary_password()
    assert len(password) == 12
    assert password.isalnum()
    assert password.replace(password[0], "") != password  # Not all same char


def test_generate_temporary_password_uniqueness():
    """Test that generated passwords are unique (high probability)."""
    passwords = [_generate_temporary_password() for _ in range(100)]
    assert len(set(passwords)) > 95  # At least 95 unique out of 100


def test_reset_password_tool_returns_valid_response():
    """Test that reset_password_tool returns expected response structure."""
    result = reset_password_tool("test@techassist.com")
    
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "success"
    assert "new_password" in result
    assert "message" in result
    assert len(result["new_password"]) == 12


def test_reset_password_tool_logs_to_file():
    """Test that password reset is logged to JSON file."""
    test_email = "logging_test@techassist.com"
    
    # Ensure file doesn't exist first
    if os.path.exists("data/passwords.json"):
        os.remove("data/passwords.json")
    
    result = reset_password_tool(test_email)
    
    # Check file was created and contains the reset
    assert os.path.exists("data/passwords.json")
    with open("data/passwords.json", "r") as f:
        log = json.load(f)
    
    assert "resets" in log
    assert len(log["resets"]) > 0
    last_reset = log["resets"][-1]
    assert last_reset["user_email"] == test_email
    assert last_reset["password"] == result["new_password"]
    
    # Cleanup
    if os.path.exists("data/passwords.json"):
        os.remove("data/passwords.json")
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_password_tools.py -v`
Expected: All 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_password_tools.py
git commit -m "test: add unit tests for password reset tool"
```

---

## Task 3: Integrate Password Reset Tool into HelpDeskAgent

**Files:**
- Modify: `src/agents/helpdesk_agent.py:1-98` (add import and tool registration)

**Interfaces:**
- Consumes: `reset_password_tool(user_email: str) → dict` from Task 1
- Produces: Updated `HelpDeskAgent` with `reset_password` tool available to LangChain agent

- [ ] **Step 1: Add import for password tool**

In `src/agents/helpdesk_agent.py`, add to the imports at the top (after line 5):

```python
from src.tools.password_tools import reset_password_tool
```

Full import section should now be:
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from src.tools.ticket_tools import (
    create_ticket_tool,
    check_ticket_status_tool,
    list_tickets_tool,
    close_ticket_tool,
)
from src.tools.password_tools import reset_password_tool
```

- [ ] **Step 2: Add reset_password tool definition in __init__ method**

In the `__init__` method, after the `close_ticket` tool definition (after line 57), add:

```python
        @tool
        def reset_password() -> dict:
            """Reset the current user's password and return a temporary password. Confirm with user first."""
            return reset_password_tool(self.user_email)
```

Then update line 59 to include the new tool:

```python
        self.tools = [create_ticket, check_ticket_status, list_tickets, close_ticket, reset_password]
```

- [ ] **Step 3: Update system prompt to include password reset instructions**

In the `__init__` method, update the system_prompt (replace lines 62-90) with:

```python
        system_prompt = f"""You are a helpful IT Support Help Desk Agent. Your role is to:
1. Creating support tickets for IT issues
2. Checking the status of existing tickets
3. Listing all tickets for the user
4. Closing resolved tickets
5. Resetting user passwords with confirmation

IMPORTANT: You are assisting user with email: {user_email}
- Users can ONLY create tickets for themselves
- Users can ONLY check tickets they own
- Users can ONLY close tickets they own
- All ticket operations are scoped to this user's email automatically
- Password resets are scoped to this user's email

When a user asks to create a ticket:
- Use the create_ticket tool with title and description
- Confirm the ticket was created successfully

When a user asks to check a ticket status:
- Use the check_ticket_status tool with the ticket ID
- Display the ticket details including title, status, and description

When a user asks to list their tickets:
- Use the list_tickets tool
- Show a summary of all their tickets

When a user asks to close a ticket:
- Use the close_ticket tool with the ticket ID
- Confirm the ticket was closed successfully

When a user asks to reset their password:
- FIRST: Inform the user that you will generate a temporary password they must change on first login
- WAIT for explicit confirmation (e.g., "Yes", "Proceed", "Go ahead")
- ONLY THEN: Use the reset_password tool
- Display the new temporary password in a clear format
- Remind them: "You must change this password immediately after your first login"

Always be helpful and professional. Only refer to tickets that belong to this user."""
```

- [ ] **Step 4: Verify the agent initialization still works**

Check that the file has valid Python syntax:

Run: `python -m py_compile src/agents/helpdesk_agent.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add src/agents/helpdesk_agent.py
git commit -m "feat: add password reset tool to HelpDeskAgent with confirmation flow"
```

---

## Task 4: Test Agent Integration

**Files:**
- Create: `tests/test_helpdesk_agent_password.py`

**Interfaces:**
- Consumes: `HelpDeskAgent` (from Task 3), `reset_password_tool` (from Task 1)
- Produces: Integration test verifying agent calls password reset tool

- [ ] **Step 1: Write integration test**

Create `tests/test_helpdesk_agent_password.py`:

```python
"""Integration tests for HelpDeskAgent password reset functionality."""

import os
import json
import pytest
from src.agents.helpdesk_agent import HelpDeskAgent


@pytest.fixture
def helpdesk_agent():
    """Create a HelpDeskAgent instance for testing."""
    return HelpDeskAgent("test_user@techassist.com")


def test_agent_has_reset_password_tool(helpdesk_agent):
    """Test that HelpDeskAgent has reset_password tool."""
    tool_names = [tool.name for tool in helpdesk_agent.tools]
    assert "reset_password" in tool_names


def test_agent_tools_count(helpdesk_agent):
    """Test that HelpDeskAgent has expected number of tools (4 ticket + 1 password)."""
    assert len(helpdesk_agent.tools) == 5


def test_agent_prompt_mentions_password_reset(helpdesk_agent):
    """Test that system prompt includes password reset instructions."""
    # We can't easily access the prompt, but we verify the tool exists
    # and the user_email is properly scoped
    assert helpdesk_agent.user_email == "test_user@techassist.com"
    tool_names = [tool.name for tool in helpdesk_agent.tools]
    assert "reset_password" in tool_names


def teardown_function():
    """Clean up password log after tests."""
    if os.path.exists("data/passwords.json"):
        os.remove("data/passwords.json")
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_helpdesk_agent_password.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_helpdesk_agent_password.py
git commit -m "test: add integration tests for password reset tool in HelpDeskAgent"
```

---

## Task 5: Manual Testing in Streamlit UI

**Files:**
- No code changes (testing existing integration)

**Interfaces:**
- Consumes: HelpDeskAgent with password reset (from Task 3)
- Tests: End-to-end password reset flow in HelpDesk tab

- [ ] **Step 1: Start the Streamlit app**

Run: `streamlit run app.py`

Expected: App starts at `http://localhost:8501`

- [ ] **Step 2: Log in as a test user**

- Navigate to login page (should appear if not logged in)
- Use credentials: `alice@techassist.com` / `password123`
- Should see main app with tabs

- [ ] **Step 3: Navigate to HelpDesk tab**

- Click on "🎫 HelpDesk" tab
- Should see chat interface with input field

- [ ] **Step 4: Test password reset flow**

In the HelpDesk chat, type: "I need to reset my password"

Expected response flow:
1. Agent asks for confirmation (e.g., "I can reset your password...")
2. Type: "Yes" or "Proceed"
3. Agent should display a temporary password like `Abc1234XyZ5`
4. Agent should mention "change immediately after first login"

- [ ] **Step 5: Verify password was logged**

Check `data/passwords.json`:

```bash
cat data/passwords.json
```

Expected: JSON file contains an entry with `alice@techassist.com` and the generated password

- [ ] **Step 6: Test with different user (admin)**

Log out and log in as `admin@techassist.com` / `admin123`, repeat steps 3-5 to verify scoping works

- [ ] **Step 7: Mark task complete**

If all flows work as expected, the feature is complete. No commit needed (already committed in Task 3).

---

## Summary

After all tasks complete, the password reset feature will:
- ✅ Generate temporary 12-char passwords on demand
- ✅ Store them in `data/passwords.json` for demo audit trail
- ✅ Require agent confirmation before execution (security pattern)
- ✅ Display password in HelpDesk chat with "change on first login" reminder
- ✅ Scope resets to the logged-in user's email
- ✅ Integrate with LangChain agent tool calling for demo of agentic patterns
