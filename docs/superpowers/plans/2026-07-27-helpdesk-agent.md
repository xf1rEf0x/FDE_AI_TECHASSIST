# Help Desk Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a LangChain-based Help Desk Agent that lets users create tickets and check their status, with local JSON persistence and per-user access control.

**Architecture:** The agent uses LangChain's `AgentExecutor` with two tools (`create_ticket` and `check_ticket_status`). Tickets are stored in `data/tickets.json` with a unique ID and owner email. The agent prompt includes an access control guard ensuring users only see/modify their own tickets. Tools return structured data; the agent decides invocation based on user intent.

**Tech Stack:** LangChain, Pydantic (for structured outputs), Python standard library (json, uuid, datetime).

## Global Constraints
- User identification: passed via `user_email` parameter (matches sidebar selection in Phase 1)
- Ticket storage: JSON file at `data/tickets.json` (auto-created if missing)
- Tool responses: Pydantic BaseModel for validation
- Agent model: Gemini (via LangChain's `ChatGoogleGenerativeAI`)
- No new external dependencies beyond existing Phase 1/2 stack

---

### Task 1: Implement Ticket Storage Layer

**Files:**
- Create: `src/storage/ticket_store.py`
- Create: `tests/test_ticket_store.py`

**Interfaces:**
- Produces: 
  - `Ticket(BaseModel)` with fields: `id: str`, `owner_email: str`, `title: str`, `description: str`, `status: str`, `created_at: str`, `updated_at: str`
  - `TicketStore` class with methods:
    - `create_ticket(owner_email: str, title: str, description: str) -> Ticket`
    - `get_ticket(ticket_id: str, owner_email: str) -> Ticket | None`
    - `list_user_tickets(owner_email: str) -> list[Ticket]`
    - `update_ticket_status(ticket_id: str, owner_email: str, status: str) -> Ticket | None`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ticket_store.py`:

```python
import pytest
from src.storage.ticket_store import Ticket, TicketStore
import tempfile
import os

@pytest.fixture
def temp_store():
    """Temporary ticket store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "tickets.json")
        store = TicketStore(store_path)
        yield store

def test_create_ticket(temp_store):
    ticket = temp_store.create_ticket(
        owner_email="alice@example.com",
        title="VPN not working",
        description="Cannot connect to corporate VPN from home"
    )
    assert ticket.id is not None
    assert ticket.owner_email == "alice@example.com"
    assert ticket.title == "VPN not working"
    assert ticket.status == "open"

def test_get_ticket_by_owner(temp_store):
    ticket = temp_store.create_ticket(
        owner_email="alice@example.com",
        title="Laptop issue",
        description="Screen flickering"
    )
    retrieved = temp_store.get_ticket(ticket.id, "alice@example.com")
    assert retrieved is not None
    assert retrieved.id == ticket.id

def test_get_ticket_denies_other_user(temp_store):
    ticket = temp_store.create_ticket(
        owner_email="alice@example.com",
        title="Laptop issue",
        description="Screen flickering"
    )
    retrieved = temp_store.get_ticket(ticket.id, "bob@example.com")
    assert retrieved is None

def test_list_user_tickets(temp_store):
    temp_store.create_ticket("alice@example.com", "Issue 1", "Desc 1")
    temp_store.create_ticket("alice@example.com", "Issue 2", "Desc 2")
    temp_store.create_ticket("bob@example.com", "Issue 3", "Desc 3")
    
    alice_tickets = temp_store.list_user_tickets("alice@example.com")
    assert len(alice_tickets) == 2
    assert all(t.owner_email == "alice@example.com" for t in alice_tickets)

def test_update_ticket_status(temp_store):
    ticket = temp_store.create_ticket("alice@example.com", "Test", "Desc")
    updated = temp_store.update_ticket_status(ticket.id, "alice@example.com", "in_progress")
    assert updated is not None
    assert updated.status == "in_progress"

def test_update_ticket_status_denies_other_user(temp_store):
    ticket = temp_store.create_ticket("alice@example.com", "Test", "Desc")
    result = temp_store.update_ticket_status(ticket.id, "bob@example.com", "closed")
    assert result is None

def test_persistence(temp_store):
    ticket = temp_store.create_ticket("alice@example.com", "Test", "Desc")
    
    new_store = TicketStore(temp_store.store_path)
    retrieved = new_store.get_ticket(ticket.id, "alice@example.com")
    assert retrieved is not None
    assert retrieved.title == "Test"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ticket_store.py -v
```

Expected: All tests fail with "ModuleNotFoundError: No module named 'src.storage.ticket_store'"

- [ ] **Step 3: Implement TicketStore**

Create `src/storage/ticket_store.py`:

```python
import json
import uuid
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

class Ticket(BaseModel):
    id: str
    owner_email: str
    title: str
    description: str
    status: str
    created_at: str
    updated_at: str

class TicketStore:
    def __init__(self, store_path: str = "data/tickets.json"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self.store_path.write_text(json.dumps({}))
    
    def _load(self) -> dict:
        return json.loads(self.store_path.read_text())
    
    def _save(self, data: dict):
        self.store_path.write_text(json.dumps(data, indent=2))
    
    def create_ticket(self, owner_email: str, title: str, description: str) -> Ticket:
        ticket_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        ticket = Ticket(
            id=ticket_id,
            owner_email=owner_email,
            title=title,
            description=description,
            status="open",
            created_at=now,
            updated_at=now
        )
        
        data = self._load()
        data[ticket_id] = ticket.model_dump()
        self._save(data)
        
        return ticket
    
    def get_ticket(self, ticket_id: str, owner_email: str) -> Ticket | None:
        data = self._load()
        if ticket_id not in data:
            return None
        
        ticket_data = data[ticket_id]
        if ticket_data["owner_email"] != owner_email:
            return None
        
        return Ticket(**ticket_data)
    
    def list_user_tickets(self, owner_email: str) -> list[Ticket]:
        data = self._load()
        return [
            Ticket(**t) for t in data.values()
            if t["owner_email"] == owner_email
        ]
    
    def update_ticket_status(self, ticket_id: str, owner_email: str, status: str) -> Ticket | None:
        data = self._load()
        if ticket_id not in data:
            return None
        
        ticket_data = data[ticket_id]
        if ticket_data["owner_email"] != owner_email:
            return None
        
        ticket_data["status"] = status
        ticket_data["updated_at"] = datetime.utcnow().isoformat()
        
        self._save(data)
        return Ticket(**ticket_data)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ticket_store.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/storage/__init__.py src/storage/ticket_store.py tests/test_ticket_store.py
git commit -m "feat: add ticket storage layer with access control"
```

---

### Task 2: Implement Ticket Tools

**Files:**
- Create: `src/tools/ticket_tools.py`
- Create: `tests/test_ticket_tools.py`

**Interfaces:**
- Consumes: `TicketStore` from Task 1
- Produces:
  - `create_ticket_tool(user_email: str, title: str, description: str) -> dict` (returns `{ticket_id, status, message}`)
  - `check_ticket_status_tool(user_email: str, ticket_id: str) -> dict` (returns `{ticket_id, status, title, description, created_at}`)
  - `list_tickets_tool(user_email: str) -> dict` (returns `{tickets: [...]})

- [ ] **Step 1: Write failing tests**

Create `tests/test_ticket_tools.py`:

```python
import pytest
from src.tools.ticket_tools import create_ticket_tool, check_ticket_status_tool, list_tickets_tool
from src.storage.ticket_store import TicketStore
import tempfile
import os

@pytest.fixture
def mock_store(monkeypatch):
    """Mock the TicketStore for tools."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "tickets.json")
        store = TicketStore(store_path)
        monkeypatch.setattr("src.tools.ticket_tools.ticket_store", store)
        yield store

def test_create_ticket_tool(mock_store):
    result = create_ticket_tool(
        user_email="alice@example.com",
        title="VPN Issue",
        description="Cannot access VPN"
    )
    assert result["status"] == "success"
    assert result["ticket_id"] is not None
    assert "VPN Issue" in result["message"]

def test_check_ticket_status_tool(mock_store):
    ticket = mock_store.create_ticket("alice@example.com", "Test", "Desc")
    result = check_ticket_status_tool("alice@example.com", ticket.id)
    assert result["status"] == "success"
    assert result["ticket"]["title"] == "Test"
    assert result["ticket"]["status"] == "open"

def test_check_ticket_status_tool_denied_other_user(mock_store):
    ticket = mock_store.create_ticket("alice@example.com", "Test", "Desc")
    result = check_ticket_status_tool("bob@example.com", ticket.id)
    assert result["status"] == "error"
    assert "access denied" in result["message"].lower()

def test_list_tickets_tool(mock_store):
    mock_store.create_ticket("alice@example.com", "Issue 1", "Desc 1")
    mock_store.create_ticket("alice@example.com", "Issue 2", "Desc 2")
    
    result = list_tickets_tool("alice@example.com")
    assert result["status"] == "success"
    assert len(result["tickets"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ticket_tools.py -v
```

Expected: Tests fail with "ModuleNotFoundError"

- [ ] **Step 3: Implement ticket tools**

Create `src/tools/ticket_tools.py`:

```python
from src.storage.ticket_store import TicketStore

ticket_store = TicketStore("data/tickets.json")

def create_ticket_tool(user_email: str, title: str, description: str) -> dict:
    """Create a new support ticket."""
    ticket = ticket_store.create_ticket(user_email, title, description)
    return {
        "status": "success",
        "ticket_id": ticket.id,
        "message": f"Ticket created successfully: {ticket.title} (ID: {ticket.id})"
    }

def check_ticket_status_tool(user_email: str, ticket_id: str) -> dict:
    """Check the status of a ticket."""
    ticket = ticket_store.get_ticket(ticket_id, user_email)
    if not ticket:
        return {
            "status": "error",
            "message": "Ticket not found or access denied."
        }
    
    return {
        "status": "success",
        "ticket": {
            "ticket_id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status,
            "created_at": ticket.created_at
        }
    }

def list_tickets_tool(user_email: str) -> dict:
    """List all tickets for the current user."""
    tickets = ticket_store.list_user_tickets(user_email)
    return {
        "status": "success",
        "tickets": [
            {
                "ticket_id": t.id,
                "title": t.title,
                "status": t.status,
                "created_at": t.created_at
            }
            for t in tickets
        ]
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ticket_tools.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tools/ticket_tools.py tests/test_ticket_tools.py
git commit -m "feat: add ticket creation and status checking tools"
```

---

### Task 3: Create Help Desk Agent with Tool Calling

**Files:**
- Create: `src/agents/helpdesk_agent.py`
- Create: `tests/test_helpdesk_agent.py`

**Interfaces:**
- Consumes: ticket tools from Task 2
- Produces:
  - `HelpDeskAgent` class with:
    - `__init__(user_email: str, model_name: str = "gemini-1.5-flash")`
    - `run(user_input: str) -> str` (returns agent response text)

- [ ] **Step 1: Write failing tests**

Create `tests/test_helpdesk_agent.py`:

```python
import pytest
from src.agents.helpdesk_agent import HelpDeskAgent
from src.storage.ticket_store import TicketStore
import tempfile
import os

@pytest.fixture
def mock_agent():
    """Create a Help Desk Agent for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "tickets.json")
        # Monkey-patch the ticket store path
        import src.tools.ticket_tools as tools
        original_store = tools.ticket_store
        tools.ticket_store = TicketStore(store_path)
        
        agent = HelpDeskAgent("alice@example.com")
        yield agent
        
        tools.ticket_store = original_store

def test_agent_creates_ticket(mock_agent):
    response = mock_agent.run("I need to create a ticket for my laptop not starting")
    assert response is not None
    assert len(response) > 0

def test_agent_receives_user_email(mock_agent):
    assert mock_agent.user_email == "alice@example.com"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_helpdesk_agent.py -v
```

Expected: Tests fail with "ModuleNotFoundError"

- [ ] **Step 3: Implement Help Desk Agent**

Create `src/agents/helpdesk_agent.py`:

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.tools.ticket_tools import (
    create_ticket_tool,
    check_ticket_status_tool,
    list_tickets_tool
)

class HelpDeskAgent:
    def __init__(self, user_email: str, model_name: str = "gemini-1.5-flash"):
        self.user_email = user_email
        self.model_name = model_name
        
        # Define LangChain tools
        @tool
        def create_ticket(title: str, description: str) -> dict:
            """Create a new support ticket."""
            return create_ticket_tool(self.user_email, title, description)
        
        @tool
        def check_ticket_status(ticket_id: str) -> dict:
            """Check the status of a specific ticket."""
            return check_ticket_status_tool(self.user_email, ticket_id)
        
        @tool
        def list_tickets() -> dict:
            """List all your support tickets."""
            return list_tickets_tool(self.user_email)
        
        self.tools = [create_ticket, check_ticket_status, list_tickets]
        
        # System prompt with access control guard
        self.system_prompt = f"""You are a helpful IT Support Help Desk Agent. Your role is to assist users with:
1. Creating support tickets for IT issues
2. Checking the status of existing tickets
3. Listing all tickets for the user

IMPORTANT: You are assisting user with email: {self.user_email}
- Users can ONLY create tickets for themselves
- Users can ONLY check tickets they own
- All ticket operations are scoped to this user's email automatically

When a user wants to create a ticket:
- Ask for a clear title and description if not provided
- Call create_ticket with the provided information
- Confirm the ticket ID with the user

When a user wants to check ticket status:
- Ask for the ticket ID if not provided
- Call check_ticket_status to retrieve information
- Present the status clearly

Always be helpful and professional. If a ticket doesn't exist or access is denied, explain this clearly."""

        # Create the agent
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        self.agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=False)
    
    def run(self, user_input: str) -> str:
        """Run the agent with user input and return response text."""
        result = self.executor.invoke({"input": user_input})
        return result.get("output", "")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_helpdesk_agent.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/agents/helpdesk_agent.py tests/test_helpdesk_agent.py
git commit -m "feat: implement Help Desk Agent with tool calling"
```

---

### Task 4: Integrate Help Desk Agent into Streamlit UI

**Files:**
- Modify: `app.py` (add HelpDesk tab and session state)
- Create: `src/ui/helpdesk_tab.py` (UI logic for Help Desk)

**Interfaces:**
- Consumes: `HelpDeskAgent` from Task 3
- Produces: Streamlit tab rendering for Help Desk with chat interface

- [ ] **Step 1: Create Help Desk UI module**

Create `src/ui/helpdesk_tab.py`:

```python
import streamlit as st
from src.agents.helpdesk_agent import HelpDeskAgent

def render_helpdesk_tab(user_email: str):
    """Render the Help Desk tab with ticket creation and status checking."""
    st.header("Help Desk")
    
    if "helpdesk_agent" not in st.session_state:
        st.session_state.helpdesk_agent = HelpDeskAgent(user_email)
    
    if "helpdesk_messages" not in st.session_state:
        st.session_state.helpdesk_messages = []
    
    # Display chat history
    for message in st.session_state.helpdesk_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    user_input = st.chat_input("Ask about creating or checking a ticket...")
    if user_input:
        st.session_state.helpdesk_messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.write(user_input)
        
        # Run agent
        with st.chat_message("assistant"):
            response = st.session_state.helpdesk_agent.run(user_input)
            st.write(response)
            st.session_state.helpdesk_messages.append({"role": "assistant", "content": response})
```

- [ ] **Step 2: Modify app.py to add Help Desk tab**

In `app.py`, update the tab logic. Find the existing tab structure and add:

```python
from src.ui.helpdesk_tab import render_helpdesk_tab

# Inside the main app after role/email selection:
tab1, tab2, tab3 = st.tabs(["Chat", "Asset Agent", "Help Desk"])

with tab1:
    render_chat_tab(user_role, user_email)

with tab2:
    render_asset_agent_tab(user_email)

with tab3:
    render_helpdesk_tab(user_email)
```

- [ ] **Step 3: Test Help Desk tab in Streamlit UI**

```bash
streamlit run app.py
```

Steps to verify:
1. Select "Employee" role and enter your email
2. Click "Help Desk" tab
3. Type: "Create a ticket for my laptop not starting"
4. Verify the agent creates a ticket and returns the ticket ID
5. Type: "Check the status of ticket [ID]"
6. Verify it returns the ticket details

- [ ] **Step 4: Commit**

```bash
git add src/ui/helpdesk_tab.py app.py
git commit -m "feat: integrate Help Desk Agent into Streamlit UI"
```

---

### Task 5: End-to-End Integration Tests

**Files:**
- Create: `tests/test_helpdesk_integration.py`

**Interfaces:**
- Consumes: All modules from Tasks 1-3
- Produces: Integration test suite verifying full workflow

- [ ] **Step 1: Write integration tests**

Create `tests/test_helpdesk_integration.py`:

```python
import pytest
import tempfile
import os
from src.agents.helpdesk_agent import HelpDeskAgent
from src.storage.ticket_store import TicketStore
import src.tools.ticket_tools as tools

@pytest.fixture
def integration_setup():
    """Set up a fresh ticket store for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "tickets.json")
        original_store = tools.ticket_store
        tools.ticket_store = TicketStore(store_path)
        
        yield tools.ticket_store
        
        tools.ticket_store = original_store

def test_create_and_check_ticket_workflow(integration_setup):
    """Test full workflow: create ticket then check its status."""
    agent = HelpDeskAgent("alice@example.com")
    
    # Simulate user creating a ticket
    create_response = agent.run("Create a ticket for my VPN is not working")
    assert "success" in create_response.lower() or "ticket" in create_response.lower()
    
    # Get the ticket ID from the response (simplified check)
    tickets = integration_setup.list_user_tickets("alice@example.com")
    assert len(tickets) == 1
    
    ticket_id = tickets[0].id
    
    # Check ticket status
    status_response = agent.run(f"Check status of ticket {ticket_id}")
    assert "success" in status_response.lower() or ticket_id in status_response

def test_access_control_enforcement(integration_setup):
    """Test that users cannot access other users' tickets."""
    alice_agent = HelpDeskAgent("alice@example.com")
    bob_agent = HelpDeskAgent("bob@example.com")
    
    # Alice creates a ticket
    alice_agent.run("Create a ticket for my laptop issue")
    alice_tickets = integration_setup.list_user_tickets("alice@example.com")
    assert len(alice_tickets) == 1
    
    alice_ticket_id = alice_tickets[0].id
    
    # Bob tries to check Alice's ticket
    bob_response = bob_agent.run(f"Check status of ticket {alice_ticket_id}")
    assert "not found" in bob_response.lower() or "access" in bob_response.lower()

def test_multiple_tickets_per_user(integration_setup):
    """Test user can create and manage multiple tickets."""
    agent = HelpDeskAgent("alice@example.com")
    
    agent.run("Create a ticket for my printer not working")
    agent.run("Create a ticket for my email access issue")
    
    tickets = integration_setup.list_user_tickets("alice@example.com")
    assert len(tickets) == 2
    assert all(t.owner_email == "alice@example.com" for t in tickets)
```

- [ ] **Step 2: Run integration tests**

```bash
pytest tests/test_helpdesk_integration.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_helpdesk_integration.py
git commit -m "test: add end-to-end Help Desk Agent integration tests"
```

---

### Task 6: Add Data Directory and Documentation

**Files:**
- Create: `data/.gitkeep` (placeholder for tickets.json)
- Create: `docs/implementation/helpdesk_agent.md` (agent documentation)

- [ ] **Step 1: Create data directory structure**

```bash
mkdir -p data
touch data/.gitkeep
```

- [ ] **Step 2: Write agent documentation**

Create `docs/implementation/helpdesk_agent.md`:

```markdown
# Help Desk Agent

## Overview

The Help Desk Agent is a LangChain-based tool-calling agent that helps employees create and track support tickets. It stores all tickets locally in JSON format with strict per-user access control.

## Features

- **Create Tickets**: Users describe their IT issue; the agent creates a ticket with auto-generated ID
- **Check Status**: Users can query the status of their tickets by ID
- **List Tickets**: Users can see all tickets they've created
- **Access Control**: Users can only see/modify tickets they own (enforced by email)

## Architecture

### Components

1. **TicketStore** (`src/storage/ticket_store.py`)
   - JSON-based ticket persistence
   - Access control on all operations (owner_email validation)
   - Methods: create_ticket, get_ticket, list_user_tickets, update_ticket_status

2. **Ticket Tools** (`src/tools/ticket_tools.py`)
   - `create_ticket_tool`: Wrapper for ticket creation
   - `check_ticket_status_tool`: Wrapper for status queries
   - `list_tickets_tool`: Wrapper for listing user tickets

3. **HelpDeskAgent** (`src/agents/helpdesk_agent.py`)
   - LangChain AgentExecutor with tool-calling
   - Gemini LLM for natural language understanding
   - System prompt enforces user context (email scoping)

### Data Model

**Ticket:**
```json
{
  "id": "uuid-string",
  "owner_email": "user@example.com",
  "title": "Issue title",
  "description": "Detailed issue description",
  "status": "open|in_progress|resolved|closed",
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp"
}
```

## Usage

### In Code

```python
from src.agents.helpdesk_agent import HelpDeskAgent

agent = HelpDeskAgent(user_email="alice@example.com")
response = agent.run("Create a ticket for my VPN is down")
print(response)
```

### In Streamlit UI

- Navigate to the "Help Desk" tab
- Chat with the agent to create, check, or list tickets
- All operations are scoped to your email (no access to other users' tickets)

## Testing

Run all tests:
```bash
pytest tests/test_ticket_store.py tests/test_ticket_tools.py tests/test_helpdesk_agent.py tests/test_helpdesk_integration.py -v
```

## Security Notes

- User email is passed from the Streamlit sidebar; in production, this should come from authenticated session
- Ticket IDs are UUIDs (not sequential, reduces guessing)
- Access control is enforced at the tool level, not just the agent level
```

- [ ] **Step 3: Commit**

```bash
git add data/.gitkeep docs/implementation/helpdesk_agent.md
git commit -m "docs: add Help Desk Agent documentation and data directory"
```

---

## Spec Coverage Checklist

- ✅ Create tickets with title/description
- ✅ Check ticket status by ID
- ✅ Local JSON persistence (data/tickets.json)
- ✅ Per-user access control (owner_email guards)
- ✅ LangChain agent with tool calling
- ✅ Streamlit UI integration
- ✅ Comprehensive tests (unit + integration)
- ✅ Documentation
