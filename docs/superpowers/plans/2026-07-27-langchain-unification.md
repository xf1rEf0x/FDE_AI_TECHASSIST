# LangChain Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace three LangGraph-based agents with a single pure LangChain unified agent that handles all IT support operations (tickets, password resets, asset lookups, software requests).

**Architecture:** One `TechAssistAgent` class using LangChain's `AgentExecutor` with `ConversationBufferMemory`. All 6 tools (ticket ops, password reset, asset lookup, software request ops) attached to one agent. Agent decides which tool to invoke based on natural language intent.

**Tech Stack:** LangChain (AgentExecutor, ConversationBufferMemory), Gemini API, Streamlit

## Global Constraints

- No LangGraph usage
- Preserve all existing tool functionality (ticket creation, software requests, asset search, password resets)
- Maintain user access control (users can only access their own resources unless admin)
- Support both employee and admin roles with appropriate tool availability
- Keep Streamlit UI unchanged (only update the integration points)

---

## File Structure

**To Create:**
- `src/agents/unified_agent.py` — Single `TechAssistAgent` class with AgentExecutor + ConversationBufferMemory

**To Modify:**
- `src/conversation.py` — Replace chain logic with unified agent; simplify to single function
- `app.py` — Update chat tab to instantiate and use unified agent
- `src/ui/helpdesk_tab.py` — Update to use unified agent instead of HelpDeskAgent

**To Delete:**
- `src/agents/helpdesk_agent.py` — LangGraph-based, replaced by unified agent
- `src/agents/software_agent.py` — LangGraph-based, replaced by unified agent
- `src/asset_agent.py` — LangGraph-based, replaced by unified agent
- `src/intent_router.py` — No longer needed; agent handles routing implicitly

---

## Task Breakdown

### Task 1: Create Unified TechAssistAgent Class

**Files:**
- Create: `src/agents/unified_agent.py`

**Interfaces:**
- Consumes: All existing tool functions from `src/tools/ticket_tools.py`, `src/tools/software_tools.py`, `src/tools/password_tools.py`, `src/asset_search_tool.py`
- Produces: `TechAssistAgent` class with:
  - `__init__(user_email: str, user_role: str = "employee", temperature: float = 0.0)`
  - `invoke(user_input: str) -> str` — returns agent response text
  - `.memory` — ConversationBufferMemory instance (for accessing chat history if needed)

- [ ] **Step 1: Create the file structure**

```python
"""Unified TechAssist agent using pure LangChain with AgentExecutor."""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.tools.ticket_tools import (
    create_ticket_tool,
    check_ticket_status_tool,
    list_tickets_tool,
    close_ticket_tool,
)
from src.tools.password_tools import reset_password_tool
from src.tools.software_tools import (
    create_software_request_tool,
    check_request_status_tool,
    list_my_requests_tool,
    list_pending_requests_tool,
    approve_request_tool,
    reject_request_tool,
)
from src.asset_search_tool import search_assets_by_employee, search_assets_by_serial, search_assets_by_type


class TechAssistAgent:
    """Unified IT support agent using LangChain AgentExecutor."""

    def __init__(self, user_email: str, user_role: str = "employee", temperature: float = 0.0):
        """Initialize unified agent.
        
        Args:
            user_email: User's email (scoped access control)
            user_role: "employee", "engineer", or "admin"
            temperature: LLM temperature (0.0 - 2.0)
        """
        self.user_email = user_email
        self.user_role = user_role
        self.is_admin = user_role == "admin"

        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            temperature=temperature,
        )

        # Initialize memory with return_messages=True for proper chat history
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
        )

        # Define all tools, scoped to user_email and user_role
        self.tools = self._define_tools()

        # Create agent prompt template
        prompt = self._create_prompt()

        # Create the tool-calling agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)

        # Create executor with memory
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=False,
            handle_parsing_errors=True,
        )

    def _define_tools(self) -> list:
        """Define all tools with user/admin scoping."""
        tools = []

        # ===== TICKET TOOLS =====
        @tool
        def create_ticket(title: str, description: str) -> str:
            """Create a new support ticket for the current user."""
            result = create_ticket_tool(self.user_email, title, description)
            return f"✓ Ticket {result['ticket_id']} created. {result['message']}"

        @tool
        def check_ticket_status(ticket_id: str) -> str:
            """Check the status of a ticket owned by the current user."""
            result = check_ticket_status_tool(self.user_email, ticket_id)
            if result["status"] == "error":
                return f"✗ {result['message']}"
            ticket = result["ticket"]
            return f"Ticket {ticket['ticket_id']}: {ticket['status']}\nTitle: {ticket['title']}\nCreated: {ticket['created_at']}"

        @tool
        def list_my_tickets() -> str:
            """List all support tickets owned by the current user."""
            result = list_tickets_tool(self.user_email)
            if not result["tickets"]:
                return "You have no tickets."
            ticket_lines = [f"- {t['id']}: {t['title']} ({t['status']})" for t in result["tickets"]]
            return f"Your tickets:\n" + "\n".join(ticket_lines)

        @tool
        def close_ticket(ticket_id: str) -> str:
            """Close a support ticket owned by the current user."""
            result = close_ticket_tool(self.user_email, ticket_id)
            if result["status"] == "error":
                return f"✗ {result['message']}"
            return f"✓ Ticket {ticket_id} closed."

        tools.extend([create_ticket, check_ticket_status, list_my_tickets, close_ticket])

        # ===== PASSWORD RESET =====
        @tool
        def reset_password() -> str:
            """Reset the current user's password and return a temporary password. Confirm with user first."""
            result = reset_password_tool(self.user_email)
            if result["status"] == "error":
                return f"✗ {result['message']}"
            return f"✓ Password reset. Temporary password: {result['temporary_password']}\nYou must change this on first login."

        tools.append(reset_password)

        # ===== ASSET LOOKUP =====
        @tool
        def lookup_assets(query: str = "", asset_type: str = "") -> str:
            """Search for employee assets. You can search by employee name or serial number."""
            # Non-admin users can only see their own assets
            search_user_id = None if self.is_admin else self.user_email.split("@")[0]
            
            results = []
            if query:
                results.extend(search_assets_by_employee(query, asset_type if asset_type else None, user_id=search_user_id, is_admin=self.is_admin))
                if not results:
                    results.extend(search_assets_by_serial(query, user_id=search_user_id, is_admin=self.is_admin))
            elif asset_type:
                results.extend(search_assets_by_type(asset_type, user_id=search_user_id, is_admin=self.is_admin))
            
            if not results:
                return f"No assets found."
            
            formatted = []
            seen_emp = set()
            for asset in results:
                emp_key = asset["employee_id"]
                if emp_key not in seen_emp:
                    formatted.append(f"\nEmployee: {asset['employee_name']} ({asset['employee_id']})")
                    formatted.append(f"Department: {asset['department']}")
                    seen_emp.add(emp_key)
                formatted.append(f"  - {asset.get('type')}: {asset.get('model', asset.get('name'))} ({asset.get('status')})")
            
            return "\n".join(formatted)

        tools.append(lookup_assets)

        # ===== SOFTWARE REQUEST TOOLS =====
        @tool
        def request_software(software_name: str, version: str, justification: str) -> str:
            """Request software installation for yourself."""
            result = create_software_request_tool(self.user_email, software_name, version, justification)
            return f"✓ Software request {result['request_id']} created. Pending admin approval."

        @tool
        def check_software_request_status(request_id: str) -> str:
            """Check the status of your software request."""
            result = check_request_status_tool(self.user_email, request_id)
            if result["status"] == "error":
                return f"✗ {result['message']}"
            req = result["request"]
            return f"Request {req['request_id']}: {req['status']}\nSoftware: {req['software_name']} {req['version']}\nRequested: {req['request_date']}"

        @tool
        def list_my_software_requests() -> str:
            """List all your software requests."""
            result = list_my_requests_tool(self.user_email)
            if not result["requests"]:
                return "You have no software requests."
            req_lines = [f"- {r['id']}: {r['software_name']} ({r['status']})" for r in result["requests"]]
            return "Your software requests:\n" + "\n".join(req_lines)

        tools.extend([request_software, check_software_request_status, list_my_software_requests])

        # ===== ADMIN-ONLY TOOLS =====
        if self.is_admin:
            @tool
            def list_pending_software_requests() -> str:
                """List all pending software requests (admin only)."""
                result = list_pending_requests_tool()
                if not result["requests"]:
                    return "No pending software requests."
                req_lines = [f"- {r['id']}: {r['software_name']} by {r['requester_email']} ({r['status']})" for r in result["requests"]]
                return "Pending requests:\n" + "\n".join(req_lines)

            @tool
            def approve_software_request(request_id: str, approved_by_name: str) -> str:
                """Approve a pending software request (admin only)."""
                result = approve_request_tool(request_id, self.user_email, approved_by_name)
                if result["status"] == "error":
                    return f"✗ {result['message']}"
                return f"✓ Request {request_id} approved."

            @tool
            def reject_software_request(request_id: str, reason: str) -> str:
                """Reject a pending software request (admin only)."""
                result = reject_request_tool(request_id, self.user_email, reason)
                if result["status"] == "error":
                    return f"✗ {result['message']}"
                return f"✓ Request {request_id} rejected. Reason: {reason}"

            tools.extend([list_pending_software_requests, approve_software_request, reject_software_request])

        return tools

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the system prompt for the agent."""
        system_message = f"""You are TechAssist AI, a helpful IT support assistant for TechAssist Solutions.

Your role is to:
1. Create and manage support tickets
2. Check ticket status and list tickets
3. Close resolved tickets
4. Reset user passwords (with confirmation)
5. Search employee assets (hardware and software licenses)
6. Handle software installation requests and approval workflow

USER CONTEXT:
- Email: {self.user_email}
- Role: {self.user_role}

PERMISSIONS:
- You can ONLY create/check/close tickets for the current user
- You can ONLY view assets for the current user (unless admin)
- You can ONLY manage software requests for the current user (unless admin)
- Admins can: list all pending requests, approve/reject requests

WORKFLOW GUIDELINES:
1. For ticket creation: Ask for title and detailed description, then create
2. For password reset: FIRST inform user of temp password requirements, WAIT for explicit confirmation, THEN reset
3. For software requests: Collect software name, version, and business justification before requesting
4. For admin approval: Always confirm requester details before approving

IMPORTANT:
- Be professional and helpful
- Always confirm actions before executing (especially destructive ones)
- Never bypass access control - enforce permission rules strictly
- Provide clear, concise responses"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        return prompt

    def invoke(self, user_input: str) -> str:
        """Run the agent with user input.
        
        Args:
            user_input: The user's message/request
            
        Returns:
            The agent's response as a string
        """
        result = self.executor.invoke({"input": user_input})
        return result.get("output", "")
```

- [ ] **Step 2: Test the file imports**

Run: `cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1" && python -c "from src.agents.unified_agent import TechAssistAgent; print('Import successful')"`
Expected: Output "Import successful"

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1"
git add src/agents/unified_agent.py
git commit -m "feat: add unified TechAssistAgent using pure LangChain AgentExecutor"
```

---

### Task 2: Simplify conversation.py

**Files:**
- Modify: `src/conversation.py`

**Interfaces:**
- Consumes: `TechAssistAgent` from `src/agents/unified_agent.py`
- Produces: Two functions:
  - `get_agent_instance(user_email: str, role: str, temperature: float) -> TechAssistAgent`
  - `get_response(user_input: str, user_email: str, role: str, temperature: float, provider: str) -> str` (backward compatible, ignores provider)

- [ ] **Step 1: Simplify conversation.py**

Replace entire file with:

```python
"""Conversation handler using unified LangChain agent."""

from src.agents.unified_agent import TechAssistAgent
from src.prompts import get_available_roles


def get_agent_instance(user_email: str, role: str, temperature: float = 0.0) -> TechAssistAgent:
    """Get a TechAssistAgent instance.
    
    Args:
        user_email: User's email
        role: "employee", "engineer", or "admin"
        temperature: LLM temperature (0.0 - 2.0)
        
    Returns:
        TechAssistAgent instance with memory
    """
    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")
    
    return TechAssistAgent(user_email, role, temperature)


def get_response(user_input: str, role: str, history: list, temperature: float = 0.7, provider: str = "huggingface") -> str:
    """Get response from unified agent (backward compatible).
    
    Args:
        user_input: User message
        role: User role
        history: Message history (ignored; agent has its own memory)
        temperature: LLM temperature
        provider: Ignored (always uses Gemini)
        
    Returns:
        Agent response text
    """
    if not user_input or not user_input.strip():
        raise ValueError("User message cannot be empty")
    
    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")
    
    # Provider parameter ignored; always use Gemini
    agent = get_agent_instance("", role, temperature)
    return agent.invoke(user_input)


def get_response_stream(user_input: str, role: str, history: list, temperature: float = 0.7, provider: str = "huggingface"):
    """Get streaming response from agent (backward compatible).
    
    Note: Unified agent doesn't support true streaming yet; yields full response in chunks.
    
    Args:
        user_input: User message
        role: User role
        history: Message history (ignored)
        temperature: LLM temperature
        provider: Ignored
        
    Yields:
        Text chunks from agent response
    """
    if not user_input or not user_input.strip():
        raise ValueError("User message cannot be empty")
    
    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")
    
    agent = get_agent_instance("", role, temperature)
    response = agent.invoke(user_input)
    
    # Simulate streaming by yielding in chunks
    chunk_size = 20
    for i in range(0, len(response), chunk_size):
        yield response[i:i + chunk_size]
```

- [ ] **Step 2: Run import test**

Run: `cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1" && python -c "from src.conversation import get_agent_instance; print('Import successful')"`
Expected: Output "Import successful"

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1"
git add src/conversation.py
git commit -m "refactor: simplify conversation.py to use unified agent"
```

---

### Task 3: Update app.py Chat Tab

**Files:**
- Modify: `app.py` (lines 215-267 — chat tab section)

**Interfaces:**
- Consumes: `get_agent_instance()` from `src/conversation.py` and current user from `src/auth.py`
- Produces: Updated chat tab that creates agent per session and uses `.invoke()`

- [ ] **Step 1: Update imports at top of app.py**

Find the line:
```python
from src.conversation import get_response, get_response_stream
```

Replace with:
```python
from src.conversation import get_agent_instance
```

- [ ] **Step 2: Update session state initialization (after line 96)**

After the line `if "messages" not in st.session_state:`, add:

```python
if "agent" not in st.session_state:
    st.session_state.agent = None
```

- [ ] **Step 3: Replace the response generation logic (lines 240-267)**

Find this block:
```python
    # Get and display assistant response after messages are shown
    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
        try:
            full_response = ""
            with st.spinner("🤔 Thinking..."):
                # Collect full response with streaming
                for chunk in get_response_stream(st.session_state.messages[-1]["content"], st.session_state.role, st.session_state.messages[:-1], temperature=st.session_state.temperature, provider=st.session_state.provider.lower()):
                    full_response += chunk

            # Add assistant message to history
            assistant_message = format_message("assistant", full_response)
            st.session_state.messages.append(assistant_message)
            ...
```

Replace with:
```python
    # Get and display assistant response after messages are shown
    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
        try:
            # Initialize agent for this session if not already done
            if st.session_state.agent is None:
                st.session_state.agent = get_agent_instance(
                    current_user["email"],
                    st.session_state.role,
                    st.session_state.temperature
                )
            
            with st.spinner("🤔 Thinking..."):
                # Get response from agent (has its own memory)
                full_response = st.session_state.agent.invoke(st.session_state.messages[-1]["content"])

            # Add assistant message to history (for Streamlit display only)
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
            info_box(str(e), "error")
        except Exception as e:
            error_msg = str(e)
            info_box(f"Error: {error_msg}", "error")
            if "API" in error_msg or "key" in error_msg.lower():
                info_box("Please check your Gemini API key in `.env` and try again.", "info")
```

- [ ] **Step 4: Verify no syntax errors**

Run: `cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1" && python -m py_compile app.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1"
git add app.py
git commit -m "refactor: update chat tab to use unified agent with session management"
```

---

### Task 4: Update helpdesk_tab.py

**Files:**
- Modify: `src/ui/helpdesk_tab.py`

**Interfaces:**
- Consumes: `get_agent_instance()` from `src/conversation.py`
- Produces: Updated helpdesk tab that uses unified agent instead of HelpDeskAgent

- [ ] **Step 1: Read current helpdesk_tab.py**

Run: `cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1" && head -50 src/ui/helpdesk_tab.py`
Get the structure to understand what to replace.

- [ ] **Step 2: Update imports**

Replace:
```python
from src.agents.helpdesk_agent import HelpDeskAgent
```

With:
```python
from src.conversation import get_agent_instance
```

- [ ] **Step 3: Replace HelpDeskAgent instantiation with unified agent**

Find where `HelpDeskAgent(email)` is called. Replace with:
```python
agent = get_agent_instance(email, "employee", temperature=0.0)
```

- [ ] **Step 4: Replace agent.run() calls with agent.invoke()**

Find all calls like:
```python
response = agent.run(user_input)
```

Replace with:
```python
response = agent.invoke(user_input)
```

- [ ] **Step 5: Test syntax**

Run: `cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1" && python -m py_compile src/ui/helpdesk_tab.py`
Expected: No output

- [ ] **Step 6: Commit**

```bash
cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1"
git add src/ui/helpdesk_tab.py
git commit -m "refactor: update helpdesk_tab to use unified agent"
```

---

### Task 5: Delete Obsolete Files

**Files:**
- Delete: `src/agents/helpdesk_agent.py`
- Delete: `src/agents/software_agent.py`
- Delete: `src/asset_agent.py`
- Delete: `src/intent_router.py`

- [ ] **Step 1: Delete files via git**

```bash
cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1"
git rm src/agents/helpdesk_agent.py
git rm src/agents/software_agent.py
git rm src/asset_agent.py
git rm src/intent_router.py
```

- [ ] **Step 2: Commit deletion**

```bash
git commit -m "chore: remove obsolete LangGraph-based agents and intent router"
```

---

### Task 6: Test Unified Agent in Isolation

**Files:**
- Test: Create a simple test script (no persistent test file needed)

- [ ] **Step 1: Create a quick test script**

```python
# test_unified_agent.py (temporary, don't commit)
from src.agents.unified_agent import TechAssistAgent

# Test basic instantiation
agent = TechAssistAgent("alice@techassist.com", "employee", temperature=0.0)
print("✓ Agent instantiated")

# Test invoke with a simple query
response = agent.invoke("What can you help me with?")
print(f"✓ Agent response: {response[:100]}...")

# Test memory (invoke twice, agent should remember)
response2 = agent.invoke("Can you list my tickets?")
print(f"✓ Second response: {response2[:100]}...")

print("\n✓ All basic tests passed")
```

- [ ] **Step 2: Run the test script**

Run: `cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1" && python test_unified_agent.py`
Expected: Three checkmarks, no errors

- [ ] **Step 3: Clean up test script**

```bash
cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1"
rm test_unified_agent.py
```

---

### Task 7: Test Chat Interface (Manual)

**Files:**
- Test: `app.py` running in Streamlit

- [ ] **Step 1: Start Streamlit app**

Run: `cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1" && streamlit run app.py`
Expected: Browser opens to localhost:8501

- [ ] **Step 2: Login**

Use demo credentials:
- Email: `alice@techassist.com`
- Password: `password123`

- [ ] **Step 3: Test basic chat flow**

Send message: "Hi, can you help me create a support ticket?"
Expected: Agent responds with greeting and offers to help

- [ ] **Step 4: Test tool invocation**

Send message: "I need to create a ticket for my laptop being slow. Title: Laptop Performance Issue. Description: My laptop has been running slowly for the past week."
Expected: Agent creates ticket and confirms with ticket ID

- [ ] **Step 5: Test memory**

Send message: "What was the ticket ID from what we just created?"
Expected: Agent references the ticket from previous message (memory working)

- [ ] **Step 6: Test asset lookup**

Send message: "Can you show me my assigned assets?"
Expected: Agent returns user's assets or "no assets found"

- [ ] **Step 7: Stop app**

Press Ctrl+C in terminal. No need to commit anything.

---

### Task 8: Final Verification and Cleanup

**Files:**
- Verify: All imports, requirements.txt, git status

- [ ] **Step 1: Check for any remaining imports of deleted files**

Run: `cd "C:\Users\tymur.kvaratskheliia\Workspace\Forward Deployed Engineer\fde_ai_1" && grep -r "from src.intent_router" . --include="*.py"`
Expected: No output (no remaining imports)

Run: `grep -r "from src.agents.helpdesk_agent" . --include="*.py"`
Expected: No output

Run: `grep -r "from src.agents.software_agent" . --include="*.py"`
Expected: No output

Run: `grep -r "from src.asset_agent" . --include="*.py"`
Expected: No output

- [ ] **Step 2: Check git status**

Run: `git status`
Expected: Clean working tree (all changes committed)

- [ ] **Step 3: View git log**

Run: `git log --oneline -10`
Expected: See all commits from this implementation

- [ ] **Step 4: No final commit needed**

All changes already committed per-task.

---

## Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| Agent architecture | 3 separate LangGraph agents | 1 unified LangChain AgentExecutor |
| Intent routing | Explicit IntentRouter class | Implicit via tool calling |
| Memory management | Manual history passing | ConversationBufferMemory built-in |
| Conversation logic | Complex chain building | Simple agent.invoke() call |
| File count | 8 (3 agents + 1 router + 4 other) | 1 unified agent |
| Codebase simplification | ~500 lines of agent code | ~350 lines (net savings) |

