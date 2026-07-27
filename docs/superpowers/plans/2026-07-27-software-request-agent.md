# Software Request Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a LangChain agent that allows users to request software installation/licenses using a tool-calling pattern, with persistent storage, access control guards, and approval workflow similar to the HelpDesk agent.

**Architecture:** Create a SoftwareRequestAgent that wraps tool functions for creating, tracking, and approving software requests. Tools persist data to JSON, enforce user scoping (can only request for themselves), and include an approval workflow. The agent uses ReAct (reason + act) via LangGraph to decide when to invoke tools based on user intent.

**Tech Stack:** LangChain (tool, create_react_agent), LangGraph, Pydantic models, JSON file storage, Gemini API.

## Global Constraints

- Access control: Users can only create/view their own software requests; admins can approve any request
- Tool returns: dict with "status" (success/error), optional data fields, and "message" string
- Storage: JSON file at `data/software_requests.json`, parallel structure to `data/tickets.json`
- Guards in system prompt: Prevent tool misuse, enforce permissions, confirm destructive actions
- Model: `gemini-3.5-flash-lite` at temperature=0 for deterministic responses

---

## File Structure

**Files to create:**
- `src/storage/software_request_store.py` — Persistent layer for software requests (similar to TicketStore)
- `src/tools/software_tools.py` — Tool implementations for request creation, status checks, approval
- `src/agents/software_agent.py` — LangChain agent with tool binding and system prompt

**Files to modify:**
- `src/tools/__init__.py` — Export new software tools
- `src/agents/__init__.py` — Export SoftwareRequestAgent
- `data/software_requests.json` — New data file (created on first run)

**Test files (optional, for future):**
- `tests/test_software_agent.py` — Integration tests for the agent

---

## Task 1: Create Software Request Store

**Files:**
- Create: `src/storage/software_request_store.py`
- Test: Run manual JSON load/save test

**Interfaces:**
- Produces: 
  - `SoftwareRequest` (Pydantic model with fields: id, requester_email, software_name, version, justification, status, request_date, approved_by, approved_date)
  - `SoftwareRequestStore` class with methods:
    - `create_request(requester_email, software_name, version, justification) -> SoftwareRequest`
    - `get_request(request_id, requester_email) -> SoftwareRequest | None` (access control)
    - `list_user_requests(requester_email) -> list[SoftwareRequest]`
    - `approve_request(request_id, approver_email, approved_by_name) -> SoftwareRequest | None` (access control)
    - `reject_request(request_id, approver_email, reason) -> SoftwareRequest | None` (access control)
    - `list_pending_requests() -> list[SoftwareRequest]` (admin only)

- [ ] **Step 1: Create SoftwareRequest Pydantic model**

Create file `src/storage/software_request_store.py` with:

```python
"""Software request storage layer with JSON persistence and access control."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel


class SoftwareRequest(BaseModel):
    """Software request data model."""

    id: str
    requester_email: str
    software_name: str
    version: str
    justification: str
    status: str = "pending"  # pending, approved, rejected
    request_date: str
    approved_by: str | None = None  # Name of approver
    approved_date: str | None = None
    rejection_reason: str | None = None
```

- [ ] **Step 2: Create SoftwareRequestStore class with basic structure**

Add to `src/storage/software_request_store.py`:

```python
class SoftwareRequestStore:
    """Manages software request storage with per-user access control."""

    def __init__(self, store_path: str = "data/software_requests.json"):
        """Initialize store, creating parent directories and empty file if missing."""
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._save([])

    def _load(self) -> list[dict]:
        """Load requests from JSON file."""
        if not self.store_path.exists():
            return []
        with open(self.store_path) as f:
            return json.load(f)

    def _save(self, requests: list[dict]) -> None:
        """Save requests to JSON file."""
        with open(self.store_path, "w") as f:
            json.dump(requests, f, indent=2)
```

- [ ] **Step 3: Implement create_request method**

Add to `SoftwareRequestStore`:

```python
    def create_request(
        self, requester_email: str, software_name: str, version: str, justification: str
    ) -> SoftwareRequest:
        """Create and persist a new software request."""
        request = SoftwareRequest(
            id=str(uuid.uuid4()),
            requester_email=requester_email,
            software_name=software_name,
            version=version,
            justification=justification,
            status="pending",
            request_date=datetime.now(timezone.utc).isoformat(),
        )
        requests = self._load()
        requests.append(request.model_dump())
        self._save(requests)
        return request
```

- [ ] **Step 4: Implement get_request method with access control**

Add to `SoftwareRequestStore`:

```python
    def get_request(self, request_id: str, requester_email: str) -> SoftwareRequest | None:
        """Get request if requester_email matches (access control enforced)."""
        requests = self._load()
        for req_data in requests:
            if req_data["id"] == request_id:
                # Access control: only return if requester matches
                if req_data["requester_email"] == requester_email:
                    return SoftwareRequest(**req_data)
                else:
                    return None
        return None
```

- [ ] **Step 5: Implement list_user_requests method**

Add to `SoftwareRequestStore`:

```python
    def list_user_requests(self, requester_email: str) -> list[SoftwareRequest]:
        """List all requests created by the user."""
        requests = self._load()
        user_requests = [
            SoftwareRequest(**r) for r in requests if r["requester_email"] == requester_email
        ]
        return user_requests
```

- [ ] **Step 6: Implement approve_request method**

Add to `SoftwareRequestStore`:

```python
    def approve_request(
        self, request_id: str, approver_email: str, approved_by_name: str
    ) -> SoftwareRequest | None:
        """Approve a pending request (admin/approver only)."""
        requests = self._load()
        for i, req_data in enumerate(requests):
            if req_data["id"] == request_id:
                if req_data["status"] != "pending":
                    return None  # Can only approve pending requests
                req_data["status"] = "approved"
                req_data["approved_by"] = approved_by_name
                req_data["approved_date"] = datetime.now(timezone.utc).isoformat()
                self._save(requests)
                return SoftwareRequest(**req_data)
        return None
```

- [ ] **Step 7: Implement reject_request method**

Add to `SoftwareRequestStore`:

```python
    def reject_request(
        self, request_id: str, approver_email: str, reason: str
    ) -> SoftwareRequest | None:
        """Reject a pending request (admin/approver only)."""
        requests = self._load()
        for i, req_data in enumerate(requests):
            if req_data["id"] == request_id:
                if req_data["status"] != "pending":
                    return None  # Can only reject pending requests
                req_data["status"] = "rejected"
                req_data["rejection_reason"] = reason
                self._save(requests)
                return SoftwareRequest(**req_data)
        return None
```

- [ ] **Step 8: Implement list_pending_requests (admin only)**

Add to `SoftwareRequestStore`:

```python
    def list_pending_requests(self) -> list[SoftwareRequest]:
        """List all pending requests (used by admins)."""
        requests = self._load()
        pending = [
            SoftwareRequest(**r) for r in requests if r["status"] == "pending"
        ]
        return pending
```

- [ ] **Step 9: Test basic store functionality**

Run in Python REPL or quick script:

```python
from src.storage.software_request_store import SoftwareRequestStore

store = SoftwareRequestStore("data/test_software_requests.json")
req = store.create_request("alice@techassist.com", "VSCode", "1.92", "Need for Python dev work")
print(f"Created request: {req.id}")

retrieved = store.get_request(req.id, "alice@techassist.com")
print(f"Retrieved: {retrieved.software_name}")

# Test access control (should return None)
denied = store.get_request(req.id, "bob@techassist.com")
print(f"Access denied correctly: {denied is None}")
```

Expected: Three assertions pass, file created at `data/test_software_requests.json`

- [ ] **Step 10: Clean up test file and commit**

```bash
rm data/test_software_requests.json
git add src/storage/software_request_store.py
git commit -m "feat: add SoftwareRequestStore with JSON persistence and access control"
```

---

## Task 2: Create Software Request Tools

**Files:**
- Create: `src/tools/software_tools.py`

**Interfaces:**
- Consumes: `SoftwareRequestStore` (from Task 1)
- Produces:
  - `create_software_request_tool(requester_email, software_name, version, justification) -> dict` with keys: status, request_id, message
  - `check_request_status_tool(requester_email, request_id) -> dict` with keys: status, request (if success), message (if error)
  - `list_my_requests_tool(requester_email) -> dict` with keys: status, requests (list of dicts)
  - `list_pending_requests_tool() -> dict` (admin) with keys: status, requests
  - `approve_request_tool(request_id, approver_email, approved_by_name) -> dict` with keys: status, request, message
  - `reject_request_tool(request_id, approver_email, reason) -> dict` with keys: status, message

- [ ] **Step 1: Create basic tool file with store instance**

Create `src/tools/software_tools.py`:

```python
"""Software request tools for the SoftwareRequestAgent."""

from src.storage.software_request_store import SoftwareRequestStore

# Module-level store instance (shared across all tool calls)
software_store = SoftwareRequestStore("data/software_requests.json")


def create_software_request_tool(
    requester_email: str, software_name: str, version: str, justification: str
) -> dict:
    """
    Create a new software request for the user.

    Args:
        requester_email: Email of the user requesting software
        software_name: Name of the software (e.g., "VSCode")
        version: Version or "latest"
        justification: Why the software is needed

    Returns:
        dict with keys: status, request_id, message
    """
    request = software_store.create_request(requester_email, software_name, version, justification)
    return {
        "status": "success",
        "request_id": request.id,
        "message": f"Software request created successfully. Request ID: {request.id}. Status: pending approval.",
    }
```

- [ ] **Step 2: Implement check_request_status_tool**

Add to `src/tools/software_tools.py`:

```python
def check_request_status_tool(requester_email: str, request_id: str) -> dict:
    """
    Check the status of a software request (owner only).

    Args:
        requester_email: Email of the user checking the request
        request_id: ID of the request to check

    Returns:
        dict with keys: status, request (if success), message (if error)
    """
    request = software_store.get_request(request_id, requester_email)
    if request is None:
        return {
            "status": "error",
            "message": "Request not found or access denied.",
        }

    return {
        "status": "success",
        "request": {
            "request_id": request.id,
            "software_name": request.software_name,
            "version": request.version,
            "justification": request.justification,
            "status": request.status,
            "request_date": request.request_date,
            "approved_by": request.approved_by,
            "approved_date": request.approved_date,
            "rejection_reason": request.rejection_reason,
        },
    }
```

- [ ] **Step 3: Implement list_my_requests_tool**

Add to `src/tools/software_tools.py`:

```python
def list_my_requests_tool(requester_email: str) -> dict:
    """
    List all software requests for the user.

    Args:
        requester_email: Email of the user

    Returns:
        dict with keys: status, requests (list of dicts)
    """
    requests = software_store.list_user_requests(requester_email)
    return {
        "status": "success",
        "requests": [
            {
                "request_id": r.id,
                "software_name": r.software_name,
                "version": r.version,
                "status": r.status,
                "request_date": r.request_date,
                "approved_by": r.approved_by,
            }
            for r in requests
        ],
    }
```

- [ ] **Step 4: Implement list_pending_requests_tool (admin)**

Add to `src/tools/software_tools.py`:

```python
def list_pending_requests_tool() -> dict:
    """
    List all pending software requests (admin tool).

    Returns:
        dict with keys: status, requests
    """
    requests = software_store.list_pending_requests()
    return {
        "status": "success",
        "requests": [
            {
                "request_id": r.id,
                "requester_email": r.requester_email,
                "software_name": r.software_name,
                "version": r.version,
                "justification": r.justification,
                "request_date": r.request_date,
            }
            for r in requests
        ],
    }
```

- [ ] **Step 5: Implement approve_request_tool**

Add to `src/tools/software_tools.py`:

```python
def approve_request_tool(
    request_id: str, approver_email: str, approved_by_name: str
) -> dict:
    """
    Approve a pending software request (admin only).

    Args:
        request_id: ID of the request to approve
        approver_email: Email of the admin approving
        approved_by_name: Name of the approver (for record)

    Returns:
        dict with keys: status, request, message
    """
    request = software_store.approve_request(request_id, approver_email, approved_by_name)
    if request is None:
        return {
            "status": "error",
            "message": "Request not found or cannot be approved (already approved/rejected).",
        }

    return {
        "status": "success",
        "request": {
            "request_id": request.id,
            "software_name": request.software_name,
            "status": request.status,
            "approved_by": request.approved_by,
            "approved_date": request.approved_date,
        },
        "message": f"Request {request_id} approved successfully.",
    }
```

- [ ] **Step 6: Implement reject_request_tool**

Add to `src/tools/software_tools.py`:

```python
def reject_request_tool(request_id: str, approver_email: str, reason: str) -> dict:
    """
    Reject a pending software request (admin only).

    Args:
        request_id: ID of the request to reject
        approver_email: Email of the admin rejecting
        reason: Reason for rejection

    Returns:
        dict with keys: status, message
    """
    request = software_store.reject_request(request_id, approver_email, reason)
    if request is None:
        return {
            "status": "error",
            "message": "Request not found or cannot be rejected (already approved/rejected).",
        }

    return {
        "status": "success",
        "message": f"Request {request_id} rejected. Reason: {reason}",
    }
```

- [ ] **Step 7: Test tools manually**

Create a quick test script:

```python
from src.tools.software_tools import (
    create_software_request_tool,
    check_request_status_tool,
    list_my_requests_tool,
    list_pending_requests_tool,
    approve_request_tool,
)

# Create a request
result = create_software_request_tool("alice@test.com", "Figma", "latest", "Design work")
print(f"Created: {result}")
req_id = result["request_id"]

# Check status
status = check_request_status_tool("alice@test.com", req_id)
print(f"Status: {status}")

# List requests
my_list = list_my_requests_tool("alice@test.com")
print(f"My requests: {my_list}")

# List pending
pending = list_pending_requests_tool()
print(f"Pending: {pending}")

# Approve
approved = approve_request_tool(req_id, "admin@test.com", "Admin User")
print(f"Approved: {approved}")
```

Expected: All operations succeed, store persists data to JSON

- [ ] **Step 8: Commit**

```bash
git add src/tools/software_tools.py
git commit -m "feat: add software request tools with approval workflow"
```

---

## Task 3: Create Software Request Agent

**Files:**
- Create: `src/agents/software_agent.py`

**Interfaces:**
- Consumes: All tools from Task 2 (create, check_status, list_my_requests, list_pending, approve, reject)
- Produces:
  - `SoftwareRequestAgent` class with methods:
    - `__init__(user_email, is_admin, model_name)`
    - `run(user_input) -> str`

- [ ] **Step 1: Create SoftwareRequestAgent class skeleton**

Create `src/agents/software_agent.py`:

```python
"""SoftwareRequestAgent: LangChain agent for software requests."""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from src.tools.software_tools import (
    create_software_request_tool,
    check_request_status_tool,
    list_my_requests_tool,
    list_pending_requests_tool,
    approve_request_tool,
    reject_request_tool,
)


class SoftwareRequestAgent:
    """
    LangChain agent for software requests.

    Handles software request creation, status checking, and approval workflow.
    Uses tool calling to invoke software request tools.
    """

    def __init__(self, user_email: str, is_admin: bool = False, model_name: str = "gemini-3.5-flash-lite"):
        """
        Initialize SoftwareRequestAgent.

        Args:
            user_email: Email of the user
            is_admin: Whether the user has admin permissions
            model_name: Name of the Gemini model to use
        """
        self.user_email = user_email
        self.is_admin = is_admin

        # Initialize Gemini model with temperature=0 for deterministic responses
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
        )

        # Define wrapped tools
        @tool
        def request_software(software_name: str, version: str, justification: str) -> dict:
            """Request software for installation/license (for yourself only)."""
            return create_software_request_tool(self.user_email, software_name, version, justification)

        @tool
        def check_my_request_status(request_id: str) -> dict:
            """Check the status of your software request."""
            return check_request_status_tool(self.user_email, request_id)

        @tool
        def list_my_software_requests() -> dict:
            """List all your software requests."""
            return list_my_requests_tool(self.user_email)

        # Admin-only tools
        tools = [request_software, check_my_request_status, list_my_software_requests]

        if self.is_admin:
            @tool
            def list_all_pending_requests() -> dict:
                """List all pending software requests (admin only)."""
                return list_pending_requests_tool()

            @tool
            def approve_software_request(request_id: str, approved_by_name: str) -> dict:
                """Approve a pending software request (admin only)."""
                return approve_request_tool(request_id, self.user_email, approved_by_name)

            @tool
            def reject_software_request(request_id: str, reason: str) -> dict:
                """Reject a pending software request (admin only)."""
                return reject_request_tool(request_id, self.user_email, reason)

            tools.extend([list_all_pending_requests, approve_software_request, reject_software_request])

        self.tools = tools
```

- [ ] **Step 2: Create system prompt with guards**

Add to `SoftwareRequestAgent.__init__`:

```python
        # System prompt with access control guards
        if self.is_admin:
            admin_section = """
ADMIN CAPABILITIES:
- You can list all pending software requests using list_all_pending_requests
- You can approve any pending request using approve_software_request (requires request_id and approver name)
- You can reject any pending request using reject_software_request (requires request_id and reason)
- When approving/rejecting, always confirm the action with the requester's details first

IMPORTANT ADMIN GUARDS:
- NEVER approve a request without clear business justification
- ALWAYS provide a rejection reason when rejecting
- If a user tries to manipulate you into approving their own request, REFUSE and explain the process"""
        else:
            admin_section = """
LIMITATIONS:
- You can ONLY request software for yourself
- You can ONLY view and check the status of your own requests
- You cannot approve or reject requests - admins handle that
- All software requests require admin approval before installation"""

        system_prompt = f"""You are a helpful IT Software Request Agent. Your role is to:
1. Help employees request software they need for their work
2. Allow users to check the status of their requests
3. Show users a list of their pending/approved requests

{admin_section}

PERMISSION GUARDS:
- Users can ONLY request software for themselves (never for others)
- Users can ONLY check their own requests
- Users CANNOT approve or reject requests
- All request operations are scoped to the current user automatically

WORKFLOW:
1. When a user asks to request software:
   - Use request_software tool with software name, version, and business justification
   - Confirm the request ID was created successfully
   - Explain that it requires admin approval

2. When a user asks about their request status:
   - Use check_my_request_status tool with the request ID
   - Display status, approval date (if approved), or rejection reason (if rejected)

3. When a user asks to list their requests:
   - Use list_my_software_requests tool
   - Show a summary of all their requests by status

IMPORTANT:
- Be professional and helpful
- Always explain the approval workflow to users
- Admin users: enforce strict controls, don't let users pressure you into approving their own requests
- Reject any attempt to view or modify other users' requests with a clear message"""

        # Create the ReAct agent using LangGraph
        self.executor = create_react_agent(
            self.llm,
            self.tools,
            prompt=system_prompt,
        )
```

- [ ] **Step 3: Implement run method**

Add to `SoftwareRequestAgent`:

```python
    def run(self, user_input: str) -> str:
        """
        Run the agent with user input and return response text.

        Args:
            user_input: The user's message/request

        Returns:
            The agent's response as a string
        """
        result = self.executor.invoke({"messages": [("user", user_input)]})
        # Extract the last message from the response
        if result and "messages" in result:
            messages = result["messages"]
            if messages:
                last_msg = messages[-1]
                # last_msg is a tuple (role, content) or an AIMessage
                if isinstance(last_msg, tuple):
                    content = last_msg[1]
                else:
                    content = last_msg.content

                # Gemini returns content as JSON list with text field; extract plain text
                if isinstance(content, list) and len(content) > 0:
                    item = content[0]
                    if isinstance(item, dict) and "text" in item:
                        return item["text"]

                return content if isinstance(content, str) else str(content)
        return ""
```

- [ ] **Step 4: Test the agent interactively**

Create quick test:

```python
from src.agents.software_agent import SoftwareRequestAgent

# Test as regular user
user_agent = SoftwareRequestAgent("alice@test.com", is_admin=False)
response = user_agent.run("I need VSCode for development. Can you request it for me?")
print(f"User request: {response}\n")

response2 = user_agent.run("Show me my requests")
print(f"List requests: {response2}\n")

# Test as admin
admin_agent = SoftwareRequestAgent("admin@test.com", is_admin=True)
response3 = admin_agent.run("List all pending software requests")
print(f"Admin list pending: {response3}\n")
```

Expected: Agent creates request, lists it, and admin sees pending

- [ ] **Step 5: Commit**

```bash
git add src/agents/software_agent.py
git commit -m "feat: implement SoftwareRequestAgent with tool calling and guards"
```

---

## Task 4: Update Module Exports

**Files:**
- Modify: `src/tools/__init__.py`
- Modify: `src/agents/__init__.py`

**Interfaces:**
- Consumes: SoftwareRequestAgent (from Task 3), software tools (from Task 2)

- [ ] **Step 1: Update src/tools/__init__.py**

Read current file first, then add exports:

```python
# Add this to src/tools/__init__.py
from src.tools.software_tools import (
    create_software_request_tool,
    check_request_status_tool,
    list_my_requests_tool,
    list_pending_requests_tool,
    approve_request_tool,
    reject_request_tool,
)

__all__ = [
    "create_software_request_tool",
    "check_request_status_tool",
    "list_my_requests_tool",
    "list_pending_requests_tool",
    "approve_request_tool",
    "reject_request_tool",
]
```

- [ ] **Step 2: Update src/agents/__init__.py**

Read current file first, then add export:

```python
# Add this to src/agents/__init__.py
from src.agents.software_agent import SoftwareRequestAgent

__all__ = ["SoftwareRequestAgent"]
```

- [ ] **Step 3: Commit**

```bash
git add src/tools/__init__.py src/agents/__init__.py
git commit -m "feat: export SoftwareRequestAgent and software tools"
```

---

## Task 5: Create Integration Tests

**Files:**
- Create: `tests/test_software_agent.py`

**Interfaces:**
- Consumes: SoftwareRequestAgent, software tools

- [ ] **Step 1: Write test for agent request creation**

Create `tests/test_software_agent.py`:

```python
"""Integration tests for SoftwareRequestAgent."""

import pytest
from src.agents.software_agent import SoftwareRequestAgent


def test_user_can_request_software():
    """Test that a user can request software."""
    agent = SoftwareRequestAgent("alice@test.com", is_admin=False)
    response = agent.run("I need Figma for design work. Can you help me request it?")
    
    assert response is not None
    assert len(response) > 0
    assert "success" in response.lower() or "created" in response.lower() or "request" in response.lower()


def test_user_can_list_their_requests():
    """Test that a user can list their own requests."""
    agent = SoftwareRequestAgent("bob@test.com", is_admin=False)
    
    # Create a request first
    agent.run("I need VSCode for development work")
    
    # Now list
    response = agent.run("Show me all my software requests")
    assert response is not None
    assert len(response) > 0


def test_admin_can_list_pending():
    """Test that admin can list pending requests."""
    # Create a request as user first
    user_agent = SoftwareRequestAgent("charlie@test.com", is_admin=False)
    user_agent.run("I need Slack")
    
    # Admin lists
    admin_agent = SoftwareRequestAgent("admin@test.com", is_admin=True)
    response = admin_agent.run("What software requests are pending?")
    assert response is not None
    assert len(response) > 0


def test_user_cannot_approve_own_request():
    """Test that user is prevented from approving their own request (via prompt guard)."""
    agent = SoftwareRequestAgent("user@test.com", is_admin=False)
    
    # User tries to approve - agent should refuse
    response = agent.run("Can you approve my own software request?")
    assert "cannot" in response.lower() or "approve" in response.lower()
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_software_agent.py -v
```

Expected: All 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_software_agent.py
git commit -m "test: add integration tests for SoftwareRequestAgent"
```

---

## Summary Checklist

- [x] Software request store created with access control
- [x] Software request tools implemented (create, check, list, approve, reject)
- [x] SoftwareRequestAgent built with ReAct pattern and guards
- [x] Module exports updated
- [x] Integration tests written
- [x] All commits created

**Key Design Decisions:**
- **Access Control Guards:** System prompt + tool scoping enforce that users can only request for themselves
- **Admin Approval Workflow:** Separate admin tools (list_pending, approve, reject) only available if `is_admin=True`
- **Storage:** Parallel JSON structure to tickets; TicketStore pattern reused
- **Tool Returns:** Consistent dict format (status, optional data, message) across all tools
- **Model & Temperature:** Gemini 3.5 flash lite at temperature=0 for deterministic responses

