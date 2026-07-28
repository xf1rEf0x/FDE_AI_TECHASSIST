# Phase 3 Multi-Agent Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Supervisor agent that orchestrates a Request Analysis Agent, an
Asset & Support Agent, and a Notification Agent (each exposed to the Supervisor as a
LangChain tool), and wire it in as the main chat agent, replacing `TechAssistAgent`
while keeping all its existing tools available.

**Architecture:** A shared multi-round tool-calling loop (`run_tool_calling_loop`)
powers the Supervisor and both LLM-backed sub-agents. Request Analysis is a single
structured-output call (no tools). The Supervisor's own tool list is the existing
Phase 2 helpdesk tools (extracted into a reusable `build_helpdesk_tools()`) plus three
new tools that each delegate to one sub-agent. Ticket creation is gated behind an
explicit user confirmation carried across chat turns via conversation memory — the
same pattern Phase 2 already uses for tickets/password resets.

**Tech Stack:** Python, LangChain (`langchain-core`, `langchain-google-genai`,
`langchain-huggingface`), Pydantic, pytest — all already in `requirements.txt`, no new
dependencies.

## Global Constraints

- No new dependencies — everything needed is already in `requirements.txt`.
- `TechAssistAgent`'s own `invoke()` behavior (single-round tool calling) is not
  changed — only its tool-definition code is extracted for reuse.
- No LangGraph or complex DAG orchestration — CLAUDE.md calls for simple sequential
  agent calls (docs/implementation/phase_3.md, CLAUDE.md "Phase 3" notes).
- Ticket creation must never happen in the same turn as its preview — always wait for
  an explicit follow-up user confirmation (matches Phase 2's human-in-the-loop pattern).
- New JSON data files follow the existing `TicketStore` convention: auto-create parent
  dir + empty `[]` file on first use, no manual seeding required.
- Existing Phase 2 test suite (`pytest tests/`) must still pass unchanged after the
  `build_helpdesk_tools` extraction.

---

### Task 1: Shared tool-calling loop

**Files:**
- Create: `src/agents/agent_loop.py`
- Test: `tests/test_agent_loop.py`

**Interfaces:**
- Produces: `run_tool_calling_loop(llm, tools: list, system_prompt: str, messages: list, max_iterations: int = 5) -> dict` returning `{"text": str, "tool_calls": list[dict], "token_usage": dict | None}` where each item in `tool_calls` is `{"name": str, "args": dict}` in call order.
- Produces: `extract_text(response) -> str` (also used standalone by later tasks if needed).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent_loop.py
"""Tests for the shared multi-round tool-calling loop."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from src.agents.agent_loop import run_tool_calling_loop


@tool
def add_one(n: int) -> str:
    """Add one to a number."""
    return str(n + 1)


def _mock_llm(responses):
    """Build a mock LLM whose bind_tools().invoke() yields responses in order."""
    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    llm = MagicMock()
    llm.bind_tools.return_value = llm_with_tools
    return llm


def test_stops_when_no_tool_calls():
    llm = _mock_llm([AIMessage(content="Hello there")])
    result = run_tool_calling_loop(llm, [add_one], "system prompt", [("user", "hi")])
    assert result["text"] == "Hello there"
    assert result["tool_calls"] == []


def test_executes_tool_call_and_feeds_result_back():
    tool_call_response = AIMessage(
        content="",
        tool_calls=[{"name": "add_one", "args": {"n": 4}, "id": "call-1"}],
    )
    final_response = AIMessage(content="The answer is 5")
    llm = _mock_llm([tool_call_response, final_response])

    result = run_tool_calling_loop(llm, [add_one], "system prompt", [("user", "add one to 4")])

    assert result["text"] == "The answer is 5"
    assert result["tool_calls"] == [{"name": "add_one", "args": {"n": 4}}]


def test_unknown_tool_name_reports_error_without_crashing():
    tool_call_response = AIMessage(
        content="",
        tool_calls=[{"name": "does_not_exist", "args": {}, "id": "call-1"}],
    )
    final_response = AIMessage(content="I couldn't do that")
    llm = _mock_llm([tool_call_response, final_response])

    result = run_tool_calling_loop(llm, [add_one], "system prompt", [("user", "go")])

    assert result["text"] == "I couldn't do that"
    assert result["tool_calls"] == [{"name": "does_not_exist", "args": {}}]


def test_stops_at_max_iterations():
    looping_response = AIMessage(
        content="",
        tool_calls=[{"name": "add_one", "args": {"n": 1}, "id": "call-x"}],
    )
    llm = _mock_llm([looping_response] * 10)

    result = run_tool_calling_loop(llm, [add_one], "system prompt", [("user", "go")], max_iterations=3)

    assert len(result["tool_calls"]) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_agent_loop.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.agent_loop'`

- [ ] **Step 3: Write the implementation**

```python
# src/agents/agent_loop.py
"""Shared multi-round tool-calling loop used by the Supervisor and its sub-agents."""

from langchain_core.messages import SystemMessage, ToolMessage


def extract_text(response) -> str:
    """Extract text from an LLM response (handles both string and list content)."""
    if not hasattr(response, "content"):
        return str(response)

    content = response.content
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "".join(parts)

    return str(content)


def _extract_usage(response) -> dict | None:
    """Pull token usage out of an LLM response, if the provider reports it."""
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return None
    return {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
    }


def _sum_usage(usages: list) -> dict | None:
    """Sum token usage across one or more LLM calls."""
    usages = [u for u in usages if u]
    if not usages:
        return None
    return {
        key: sum(u[key] for u in usages)
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }


def run_tool_calling_loop(
    llm, tools: list, system_prompt: str, messages: list, max_iterations: int = 5
) -> dict:
    """Run a bind_tools loop until the model stops calling tools or max_iterations is hit.

    Args:
        llm: A LangChain chat model (not yet bound to tools).
        tools: List of @tool-decorated callables.
        system_prompt: System prompt text, prepended as a SystemMessage.
        messages: List of (role, content) tuples or BaseMessage instances forming the
            conversation so far. The latest user turn must already be included.
        max_iterations: Maximum number of tool-calling rounds before giving up.

    Returns:
        dict with keys:
            - text: final response text
            - tool_calls: list of {"name": str, "args": dict} in call order
            - token_usage: summed {"input_tokens", "output_tokens", "total_tokens"} or None
    """
    llm_with_tools = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}
    convo = [SystemMessage(system_prompt)] + list(messages)
    tool_calls_made = []
    usages = []

    response = None
    for _ in range(max_iterations):
        response = llm_with_tools.invoke(convo)
        convo.append(response)
        usages.append(_extract_usage(response))

        if not getattr(response, "tool_calls", None):
            break

        for tool_call in response.tool_calls:
            tool = tools_by_name.get(tool_call["name"])
            if tool is None:
                result = f"Error: unknown tool {tool_call['name']}"
            else:
                try:
                    result = tool.invoke(tool_call["args"])
                except Exception as e:
                    result = f"Error: {e}"
            tool_calls_made.append({"name": tool_call["name"], "args": tool_call["args"]})
            convo.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    return {
        "text": extract_text(response) if response is not None else "",
        "tool_calls": tool_calls_made,
        "token_usage": _sum_usage(usages),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_agent_loop.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/agent_loop.py tests/test_agent_loop.py
git commit -m "feat: add shared multi-round tool-calling loop for Phase 3 agents"
```

---

### Task 2: Request Analysis Agent

**Files:**
- Create: `src/agents/request_analysis_agent.py`
- Test: `tests/test_request_analysis_agent.py`

**Interfaces:**
- Produces: `RequestAnalysis` (Pydantic model with fields `issue: str`, `device: str`, `action: str`).
- Produces: `analyze_request(llm, user_message: str) -> RequestAnalysis`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_request_analysis_agent.py
"""Tests for the Request Analysis Agent (structured-output extraction)."""

from unittest.mock import MagicMock
from src.agents.request_analysis_agent import analyze_request, RequestAnalysis


def test_analyze_request_returns_structured_output():
    expected = RequestAnalysis(issue="VPN Connection", device="Company Laptop", action="Create Ticket")
    structured_llm = MagicMock()
    structured_llm.invoke.return_value = expected
    llm = MagicMock()
    llm.with_structured_output.return_value = structured_llm

    result = analyze_request(llm, "My laptop isn't connecting to the company VPN, create a ticket.")

    llm.with_structured_output.assert_called_once_with(RequestAnalysis)
    assert structured_llm.invoke.call_count == 1
    assert result == expected


def test_request_analysis_model_requires_all_fields():
    analysis = RequestAnalysis(issue="Password Reset", device="Unknown", action="Reset Password")
    assert analysis.issue == "Password Reset"
    assert analysis.device == "Unknown"
    assert analysis.action == "Reset Password"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_request_analysis_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.request_analysis_agent'`

- [ ] **Step 3: Write the implementation**

```python
# src/agents/request_analysis_agent.py
"""Request Analysis Agent: extracts issue/device/action from free-form text via structured output."""

from pydantic import BaseModel, Field


class RequestAnalysis(BaseModel):
    """Structured extraction of an IT support request."""

    issue: str = Field(description="The type of issue, e.g. 'VPN Connection', 'Password Reset'")
    device: str = Field(description="The device involved, e.g. 'Company Laptop'. Use 'Unknown' if not mentioned.")
    action: str = Field(description="The action required, e.g. 'Create Ticket', 'Check Warranty'")


def analyze_request(llm, user_message: str) -> RequestAnalysis:
    """Run the Request Analysis Agent: a single structured-output LLM call."""
    structured_llm = llm.with_structured_output(RequestAnalysis)
    return structured_llm.invoke(
        "Extract the issue type, device, and required action from this IT support "
        f"request. Request: {user_message}"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_request_analysis_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/request_analysis_agent.py tests/test_request_analysis_agent.py
git commit -m "feat: add Request Analysis Agent with structured output"
```

---

### Task 3: Warranty check tool

**Files:**
- Create: `src/tools/warranty_tools.py`
- Test: `tests/test_warranty_tools.py`

**Interfaces:**
- Consumes: `search_assets_by_employee(employee_name, asset_type=None, user_id=None, is_admin=False) -> list[dict]` and `search_assets_by_serial(serial_number, user_id=None, is_admin=False) -> list[dict]` from `src/tools/asset_search_tool.py` (existing).
- Produces: `check_asset_warranty` (a `@tool`-decorated callable): `check_asset_warranty.invoke({"query": str, "user_id": str | None, "is_admin": bool}) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_warranty_tools.py
"""Tests for asset warranty/license check tool."""

from datetime import date
from src.tools.warranty_tools import check_asset_warranty
from src.tools.asset_search_tool import search_assets_by_employee


class TestCheckAssetWarranty:
    def test_reports_status_for_each_asset(self):
        """Warranty check reports ACTIVE or EXPIRED per asset, matching the raw data."""
        result = check_asset_warranty.invoke({"query": "Alice Johnson"})
        assets = search_assets_by_employee("Alice Johnson")
        assert assets, "fixture data must contain Alice's assets"

        for asset in assets:
            expiry = asset.get("warranty_end") or asset.get("expiry_date")
            expected_status = "ACTIVE" if date.fromisoformat(expiry) >= date.today() else "EXPIRED"
            assert asset["asset_id"] in result
            assert expected_status in result

    def test_search_by_serial_number(self):
        """Warranty check also matches by serial number."""
        result = check_asset_warranty.invoke({"query": "C02XQ8NWLXJX"})
        assert "LAP-2024-001" in result

    def test_no_match_returns_message(self):
        """Unknown query returns a clear no-match message, not an error."""
        result = check_asset_warranty.invoke({"query": "NoSuchEmployee999"})
        assert "No asset found" in result

    def test_scoped_to_user_id_when_not_admin(self):
        """Non-admin user_id scoping hides other employees' assets."""
        result = check_asset_warranty.invoke({"query": "Bob Smith", "user_id": "EMP001", "is_admin": False})
        assert "No asset found" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_warranty_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.tools.warranty_tools'`

- [ ] **Step 3: Write the implementation**

```python
# src/tools/warranty_tools.py
"""LangChain tool for checking employee asset warranty/license status."""

from datetime import date
from langchain_core.tools import tool

from src.tools.asset_search_tool import search_assets_by_employee, search_assets_by_serial


def _is_active(expiry: str | None) -> bool:
    """Return True if the given ISO date string is today or later."""
    if not expiry:
        return False
    return date.fromisoformat(expiry) >= date.today()


@tool
def check_asset_warranty(query: str, user_id: str = None, is_admin: bool = False) -> str:
    """Check whether an employee's asset warranty or software license is still active.

    Args:
        query: Employee name or serial/license key to look up.
        user_id: Optional current user's employee ID for access control.
        is_admin: Whether the current user is admin (bypasses user_id filter).

    Returns:
        Formatted string reporting ACTIVE/EXPIRED status per matching asset.
    """
    results = search_assets_by_employee(query, user_id=user_id, is_admin=is_admin)
    if not results:
        results = search_assets_by_serial(query, user_id=user_id, is_admin=is_admin)

    if not results:
        return f"No asset found matching '{query}'."

    lines = []
    for asset in results:
        expiry = asset.get("warranty_end") or asset.get("expiry_date")
        status = "ACTIVE" if _is_active(expiry) else "EXPIRED"
        label = asset.get("model") or asset.get("name") or asset.get("asset_id")
        expiry_note = f"expires {expiry}" if expiry else "no expiry date on file"
        lines.append(f"{asset['asset_id']} ({label}): warranty/license {status} ({expiry_note})")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_warranty_tools.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/tools/warranty_tools.py tests/test_warranty_tools.py
git commit -m "feat: add asset warranty/license check tool"
```

---

### Task 4: Support summary storage and tool

**Files:**
- Create: `src/storage/summary_store.py`
- Create: `src/tools/summary_tools.py`
- Test: `tests/test_summary_store.py`
- Test: `tests/test_summary_tools.py`

**Interfaces:**
- Produces: `SupportSummary` (Pydantic model: `id, user_email, summary, ticket_id: str | None, created_at`).
- Produces: `SummaryStore(store_path="data/support_summaries.json")` with `.save_summary(user_email, summary, ticket_id=None) -> SupportSummary` and `.list_summaries(user_email) -> list[SupportSummary]`.
- Produces: `generate_summary_tool(user_email: str, summary: str, ticket_id: str = None) -> dict` with keys `status, summary_id, message`. Module-level `summary_store` instance (patchable in tests, mirrors `src/tools/ticket_tools.py`'s `ticket_store`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_summary_store.py
"""Tests for support summary storage layer."""

import json
from datetime import datetime
from src.storage.summary_store import SupportSummary, SummaryStore


class TestSummaryStoreInit:
    def test_init_creates_store_path(self, tmp_path):
        store_path = tmp_path / "sub" / "summaries.json"
        SummaryStore(str(store_path))
        assert store_path.parent.exists()

    def test_init_creates_empty_json_file(self, tmp_path):
        store_path = tmp_path / "summaries.json"
        SummaryStore(str(store_path))
        assert store_path.exists()
        with open(store_path) as f:
            assert json.load(f) == []


class TestSaveSummary:
    def test_save_summary_fields(self, tmp_path):
        store = SummaryStore(str(tmp_path / "summaries.json"))
        record = store.save_summary(
            "alice@example.com", "VPN ticket created and warranty checked.", ticket_id="tkt-1"
        )
        assert record.user_email == "alice@example.com"
        assert record.summary == "VPN ticket created and warranty checked."
        assert record.ticket_id == "tkt-1"
        assert record.id
        datetime.fromisoformat(record.created_at)

    def test_save_summary_persists(self, tmp_path):
        store_path = tmp_path / "summaries.json"
        store = SummaryStore(str(store_path))
        store.save_summary("bob@example.com", "Summary text")
        with open(store_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["user_email"] == "bob@example.com"


class TestListSummaries:
    def test_list_returns_only_users_summaries(self, tmp_path):
        store = SummaryStore(str(tmp_path / "summaries.json"))
        store.save_summary("alice@example.com", "A summary")
        store.save_summary("bob@example.com", "B summary")
        alice_summaries = store.list_summaries("alice@example.com")
        assert len(alice_summaries) == 1
        assert alice_summaries[0].user_email == "alice@example.com"

    def test_list_empty_for_unknown_user(self, tmp_path):
        store = SummaryStore(str(tmp_path / "summaries.json"))
        assert store.list_summaries("nobody@example.com") == []
```

```python
# tests/test_summary_tools.py
"""Tests for generate_summary_tool."""

from unittest.mock import MagicMock
from src.tools.summary_tools import generate_summary_tool
from src.storage.summary_store import SupportSummary, SummaryStore


def test_generate_summary_tool(monkeypatch):
    mock_store = MagicMock(spec=SummaryStore)
    mock_store.save_summary.return_value = SupportSummary(
        id="sum-123",
        user_email="alice@company.com",
        summary="Ticket created, warranty active.",
        ticket_id="tkt-1",
        created_at="2026-07-28T10:00:00+00:00",
    )
    monkeypatch.setattr("src.tools.summary_tools.summary_store", mock_store)

    result = generate_summary_tool("alice@company.com", "Ticket created, warranty active.", "tkt-1")

    assert result["status"] == "success"
    assert result["summary_id"] == "sum-123"
    assert "sum-123" in result["message"]
    mock_store.save_summary.assert_called_once_with(
        "alice@company.com", "Ticket created, warranty active.", "tkt-1"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_summary_store.py tests/test_summary_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.storage.summary_store'`

- [ ] **Step 3: Write the implementations**

```python
# src/storage/summary_store.py
"""Support summary storage layer (mirrors TicketStore's shape)."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel


class SupportSummary(BaseModel):
    """A saved summary of a support interaction."""

    id: str
    user_email: str
    summary: str
    ticket_id: str | None = None
    created_at: str


class SummaryStore:
    """Manages support summary storage."""

    def __init__(self, store_path: str = "data/support_summaries.json"):
        """Initialize store, creating parent directories and empty file if missing."""
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._save([])

    def save_summary(
        self, user_email: str, summary: str, ticket_id: str | None = None
    ) -> SupportSummary:
        """Create and persist a new summary record."""
        record = SupportSummary(
            id=str(uuid.uuid4()),
            user_email=user_email,
            summary=summary,
            ticket_id=ticket_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        records = self._load()
        records.append(record.model_dump())
        self._save(records)
        return record

    def list_summaries(self, user_email: str) -> list[SupportSummary]:
        """List all summaries for the user."""
        records = self._load()
        return [SupportSummary(**r) for r in records if r["user_email"] == user_email]

    def _load(self) -> list[dict]:
        """Load summaries from JSON file."""
        if not self.store_path.exists():
            return []
        with open(self.store_path) as f:
            return json.load(f)

    def _save(self, records: list[dict]) -> None:
        """Save summaries to JSON file."""
        with open(self.store_path, "w") as f:
            json.dump(records, f, indent=2)
```

```python
# src/tools/summary_tools.py
"""Tool for saving a support interaction summary (used by the Notification Agent)."""

from src.storage.summary_store import SummaryStore

# Module-level store instance (shared across all tool calls), same pattern as
# src/tools/ticket_tools.py's ticket_store.
summary_store = SummaryStore("data/support_summaries.json")


def generate_summary_tool(user_email: str, summary: str, ticket_id: str = None) -> dict:
    """
    Save a support interaction summary.

    Args:
        user_email: Email of the user the summary is for.
        summary: Human-readable summary text.
        ticket_id: Optional related ticket ID.

    Returns:
        dict with keys:
            - status: "success"
            - summary_id: ID of the saved summary
            - message: Human-readable confirmation message
    """
    record = summary_store.save_summary(user_email, summary, ticket_id)
    return {
        "status": "success",
        "summary_id": record.id,
        "message": f"Summary {record.id} saved.",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_summary_store.py tests/test_summary_tools.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/storage/summary_store.py src/tools/summary_tools.py tests/test_summary_store.py tests/test_summary_tools.py
git commit -m "feat: add support summary storage and generate_summary tool"
```

---

### Task 4b: Warranty and Summary data files are git-ignored like other data files

**Files:**
- Modify: `.gitignore` (only if `data/*.json` isn't already ignored — check first)

- [ ] **Step 1: Check whether generated data files are already ignored**

Run: `git check-ignore -v data/tickets.json`

If this prints a matching rule, **skip this task** — `data/support_summaries.json` will
be ignored the same way once created (no edit needed). If it prints nothing (not
ignored), continue to Step 2.

- [ ] **Step 2: Add the ignore rule and commit**

Add `data/support_summaries.json` to `.gitignore` (matching however the existing
`data/tickets.json` etc. are — or aren't — listed there), then:

```bash
git add .gitignore
git commit -m "chore: ignore generated support summary data file"
```

---

### Task 5: Extract `build_helpdesk_tools` from `TechAssistAgent`

**Files:**
- Modify: `src/agents/unified_agent.py`

**Interfaces:**
- Produces: `build_helpdesk_tools(user_email: str, user_role: str, employee_id: str, rag_retriever: RAGRetriever) -> list` (module-level function in `src/agents/unified_agent.py`), returning the exact same tool list `TechAssistAgent` builds today.
- `TechAssistAgent._define_tools` becomes a one-line wrapper around it. No behavior change.

This is a pure refactor (extract method → module function), so there's no new test —
the existing Phase 2 test suite is the regression check.

- [ ] **Step 1: Rename the module-level RAG retriever and extract the tool-building function**

In `src/agents/unified_agent.py`, replace the module-level retriever declaration:

```python
# Loaded once at import time and shared across agent instances/sessions —
# parsing the PDFs on every login/provider-switch would be wasted work.
_rag_retriever = RAGRetriever()
```

with:

```python
# Loaded once at import time and shared across agent instances/sessions —
# parsing the PDFs on every login/provider-switch would be wasted work.
rag_retriever = RAGRetriever()
```

Then replace the entire `_define_tools` method (currently `def _define_tools(self) -> list:`
through its closing `return tools`) with a thin wrapper:

```python
    def _define_tools(self) -> list:
        """
        Define all tools scoped to user_email and user_role.

        Returns:
            List of LangChain Tool objects
        """
        return build_helpdesk_tools(self.user_email, self.user_role, self.employee_id, rag_retriever)
```

and add the extracted module-level function directly above the `TechAssistAgent` class
(after the `rag_retriever = RAGRetriever()` line), containing the exact body the method
used to have, with `self.user_email` / `self.user_role` / `self.employee_id` replaced by
the function's own parameters, and `_rag_retriever` replaced by the `rag_retriever`
parameter:

```python
def build_helpdesk_tools(
    user_email: str, user_role: str, employee_id: str, rag_retriever: RAGRetriever
) -> list:
    """
    Define all helpdesk tools scoped to user_email and user_role.

    Returns:
        List of LangChain Tool objects
    """
    # ===== Ticket Tools =====
    @tool
    def create_ticket(title: str, description: str) -> str:
        """Create a new support ticket for the current user. Only call after the user has confirmed the previewed template."""
        result = create_ticket_tool(user_email, title, description)
        return f"Ticket created: {result['message']} (ID: {result['ticket_id']})"

    @tool
    def check_ticket_status(ticket_id: str) -> str:
        """Check the status of a support ticket owned by the current user."""
        result = check_ticket_status_tool(user_email, ticket_id)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        ticket = result["ticket"]
        return (
            f"Ticket {ticket['ticket_id']}: {ticket['title']}\n"
            f"Status: {ticket['status']}\n"
            f"Created: {ticket['created_at']}\n"
            f"Description: {ticket['description']}"
        )

    @tool
    def list_my_tickets() -> str:
        """List all support tickets owned by the current user."""
        result = list_tickets_tool(user_email)
        tickets = result["tickets"]
        if not tickets:
            return "No tickets found."
        ticket_list = "\n".join(
            [
                f"- {t['ticket_id']}: {t['title']} ({t['status']})"
                for t in tickets
            ]
        )
        return f"Your tickets:\n{ticket_list}"

    @tool
    def close_ticket(ticket_id: str) -> str:
        """Close a support ticket owned by the current user."""
        result = close_ticket_tool(user_email, ticket_id)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        return f"Ticket {ticket_id} closed successfully."

    # ===== Password Tool =====
    @tool
    def reset_password() -> str:
        """Raise a password reset request for the current user (does not change the password directly). Only call after the user has confirmed the previewed template."""
        result = reset_password_tool(user_email)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        return f"Password reset request raised: {result['message']} (Request ID: {result['request_id']})"

    # ===== Software Request Tools =====
    @tool
    def request_software(
        software_name: str, version: str, justification: str
    ) -> str:
        """Request new software installation. Only call after the user has confirmed the previewed template."""
        result = create_software_request_tool(
            user_email, software_name, version, justification
        )
        return f"Software request created: {result['message']}"

    @tool
    def check_software_request_status(request_id: str) -> str:
        """Check the status of a software request owned by the current user."""
        result = check_request_status_tool(user_email, request_id)
        if result["status"] == "error":
            return f"Error: {result['message']}"
        req = result["request"]
        return (
            f"Software Request {req['request_id']}: {req['software_name']}\n"
            f"Version: {req['version']}\n"
            f"Status: {req['status']}\n"
            f"Requested: {req['request_date']}\n"
            f"Justification: {req['justification']}\n"
            f"Approved by: {req['approved_by'] or 'Pending'}"
        )

    @tool
    def list_my_software_requests() -> str:
        """List all software requests owned by the current user."""
        result = list_my_requests_tool(user_email)
        requests = result["requests"]
        if not requests:
            return "No software requests found."
        req_list = "\n".join(
            [
                f"- {r['request_id']}: {r['software_name']} v{r['version']} ({r['status']})"
                for r in requests
            ]
        )
        return f"Your software requests:\n{req_list}"

    # ===== Knowledge Base (RAG) Tool =====
    @tool
    def search_knowledge_base(query: str) -> str:
        """Search internal IT documentation (VPN, password/account troubleshooting, etc.) for an answer."""
        context = rag_retriever.format_context(query)
        return context or "No relevant documentation found."

    # ===== Asset Lookup Tool =====
    @tool
    def lookup_assets(query: str, asset_type: str = None) -> str:
        """
        Search for employee assets by name, serial number, or type.

        Args:
            query: Search query (employee name or serial number)
            asset_type: Optional asset type filter (Laptop, Monitor, Printer, Software License)
        """
        result = search_employee_assets.invoke({
            "query": query,
            "asset_type": asset_type,
            "user_id": employee_id,
            "is_admin": user_role == "admin",
        })
        return result

    # Build base tools list
    tools = [
        create_ticket,
        check_ticket_status,
        list_my_tickets,
        close_ticket,
        reset_password,
        request_software,
        check_software_request_status,
        list_my_software_requests,
        search_knowledge_base,
        lookup_assets,
    ]

    # Admin-only tools
    if user_role == "admin":

        @tool
        def list_pending_software_requests() -> str:
            """List all pending software requests (admin only)."""
            result = list_pending_requests_tool()
            requests = result["requests"]
            if not requests:
                return "No pending software requests."
            req_list = "\n".join(
                [
                    f"- {r['request_id']}: {r['software_name']} v{r['version']} "
                    f"(requested by {r['requester_email']} on {r['request_date']})"
                    for r in requests
                ]
            )
            return f"Pending software requests:\n{req_list}"

        @tool
        def approve_software_request(
            request_id: str, approved_by_name: str
        ) -> str:
            """Approve a pending software request (admin only)."""
            result = approve_request_tool(
                request_id, user_email, approved_by_name
            )
            if result["status"] == "error":
                return f"Error: {result['message']}"
            return f"Request {request_id} approved successfully."

        @tool
        def reject_software_request(request_id: str, reason: str) -> str:
            """Reject a pending software request (admin only)."""
            result = reject_request_tool(request_id, user_email, reason)
            if result["status"] == "error":
                return f"Error: {result['message']}"
            return f"Request {request_id} rejected. Reason: {reason}"

        @tool
        def unlock_account(target_email: str) -> str:
            """Unlock a user's account so they can log in again (admin only). Clarify the target email first if not already given."""
            result = unlock_account_tool(target_email)
            if result["status"] == "error":
                return f"Error: {result['message']}"
            return result["message"]

        @tool
        def list_password_reset_requests() -> str:
            """List all pending password reset requests (admin only)."""
            result = list_pending_password_reset_requests_tool()
            requests = result["requests"]
            if not requests:
                return "No pending password reset requests."
            req_list = "\n".join(
                [
                    f"- {r['request_id']}: {r['user_email']} (requested on {r['requested_at']})"
                    for r in requests
                ]
            )
            return f"Pending password reset requests:\n{req_list}"

        tools.extend(
            [
                list_pending_software_requests,
                approve_software_request,
                reject_software_request,
                unlock_account,
                list_password_reset_requests,
            ]
        )

    return tools
```

- [ ] **Step 2: Run the full existing test suite to confirm no regression**

Run: `venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS — same pass count as before this change (this is a pure extraction;
no test file references `_define_tools` directly, so nothing should need updating).

- [ ] **Step 3: Commit**

```bash
git add src/agents/unified_agent.py
git commit -m "refactor: extract build_helpdesk_tools from TechAssistAgent for reuse"
```

---

### Task 6: Asset & Support Agent

**Files:**
- Create: `src/agents/asset_support_agent.py`
- Test: `tests/test_asset_support_agent.py`

**Interfaces:**
- Consumes: `run_tool_calling_loop` from Task 1; `search_employee_assets` from `src/tools/asset_search_tool.py`; `check_asset_warranty` from Task 3; `create_ticket_tool` from `src/tools/ticket_tools.py` (existing).
- Produces: `run_asset_support_agent(llm, user_email: str, employee_id: str, is_admin: bool, instruction: str, context: str = "") -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_asset_support_agent.py
"""Tests for the Asset & Support Agent."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from src.agents import asset_support_agent as asa


def _mock_llm(responses):
    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    llm = MagicMock()
    llm.bind_tools.return_value = llm_with_tools
    return llm


def test_lookup_instruction_never_creates_ticket(monkeypatch):
    monkeypatch.setattr(asa, "search_employee_assets", MagicMock(invoke=MagicMock(return_value="Laptop found.")))
    monkeypatch.setattr(asa, "check_asset_warranty", MagicMock(invoke=MagicMock(return_value="ACTIVE")))
    create_ticket_mock = MagicMock()
    monkeypatch.setattr(asa, "create_ticket_tool", create_ticket_mock)

    responses = [
        AIMessage(content="", tool_calls=[{"name": "search_asset", "args": {"query": "Alice"}, "id": "1"}]),
        AIMessage(content="", tool_calls=[{"name": "check_warranty", "args": {"query": "Alice"}, "id": "2"}]),
        AIMessage(content="Found the laptop, warranty is active."),
    ]
    llm = _mock_llm(responses)

    result = asa.run_asset_support_agent(
        llm, "alice@company.com", "EMP001", False,
        instruction="Look up the asset and check warranty only, do not create a ticket.",
        context="Issue: VPN Connection, Device: Company Laptop",
    )

    assert "warranty is active" in result
    create_ticket_mock.assert_not_called()


def test_confirmed_instruction_creates_ticket(monkeypatch):
    monkeypatch.setattr(asa, "search_employee_assets", MagicMock())
    monkeypatch.setattr(asa, "check_asset_warranty", MagicMock())
    create_ticket_mock = MagicMock(
        return_value={"status": "success", "ticket_id": "tkt-1", "message": "Ticket tkt-1 created successfully."}
    )
    monkeypatch.setattr(asa, "create_ticket_tool", create_ticket_mock)

    responses = [
        AIMessage(
            content="",
            tool_calls=[{"name": "create_ticket", "args": {"title": "VPN issue", "description": "Cannot connect"}, "id": "1"}],
        ),
        AIMessage(content="Ticket tkt-1 created."),
    ]
    llm = _mock_llm(responses)

    result = asa.run_asset_support_agent(
        llm, "alice@company.com", "EMP001", False,
        instruction="The user confirmed. Create the ticket now.",
        context="Issue: VPN Connection, Device: Company Laptop",
    )

    assert "tkt-1" in result
    create_ticket_mock.assert_called_once_with("alice@company.com", "VPN issue", "Cannot connect")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_asset_support_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.asset_support_agent'`

- [ ] **Step 3: Write the implementation**

```python
# src/agents/asset_support_agent.py
"""Asset & Support Agent: searches assets, checks warranty, and creates tickets."""

from langchain_core.tools import tool

from src.agents.agent_loop import run_tool_calling_loop
from src.tools.asset_search_tool import search_employee_assets
from src.tools.warranty_tools import check_asset_warranty
from src.tools.ticket_tools import create_ticket_tool

ASSET_SUPPORT_SYSTEM_PROMPT = """You are the Asset & Support Agent, part of TechAssist \
AI's support workflow. You are given an instruction and context describing the user's \
issue and device.

- Use search_asset to find the employee's device/asset.
- Use check_warranty to determine whether its warranty or license is still active.
- Use create_ticket to create a support ticket.

HARD RULE: only call create_ticket if the instruction explicitly states the user has \
confirmed ticket creation. If the instruction only asks you to look up the asset and/or \
warranty, do NOT call create_ticket under any circumstances.

Respond with a short plain-text summary of what you found or did."""


def _build_tools(user_email: str, employee_id: str, is_admin: bool) -> list:
    @tool
    def search_asset(query: str, asset_type: str = None) -> str:
        """Search for the employee's asset by name, serial number, or type."""
        return search_employee_assets.invoke(
            {"query": query, "asset_type": asset_type, "user_id": employee_id, "is_admin": is_admin}
        )

    @tool
    def check_warranty(query: str) -> str:
        """Check whether an asset's warranty or license is still active."""
        return check_asset_warranty.invoke(
            {"query": query, "user_id": employee_id, "is_admin": is_admin}
        )

    @tool
    def create_ticket(title: str, description: str) -> str:
        """Create a support ticket. Only call when explicitly told the user confirmed."""
        result = create_ticket_tool(user_email, title, description)
        return f"Ticket created: {result['message']} (ID: {result['ticket_id']})"

    return [search_asset, check_warranty, create_ticket]


def run_asset_support_agent(
    llm, user_email: str, employee_id: str, is_admin: bool, instruction: str, context: str = ""
) -> str:
    """Run the Asset & Support Agent for one delegated task."""
    tools = _build_tools(user_email, employee_id, is_admin)
    messages = [("user", f"Instruction: {instruction}\n\nContext:\n{context}")]
    result = run_tool_calling_loop(llm, tools, ASSET_SUPPORT_SYSTEM_PROMPT, messages)
    return result["text"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_asset_support_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/asset_support_agent.py tests/test_asset_support_agent.py
git commit -m "feat: add Asset & Support Agent"
```

---

### Task 7: Notification Agent

**Files:**
- Create: `src/agents/notification_agent.py`
- Test: `tests/test_notification_agent.py`

**Interfaces:**
- Consumes: `run_tool_calling_loop` from Task 1; `generate_summary_tool` from Task 4.
- Produces: `run_notification_agent(llm, user_email: str, instruction: str, context: str = "") -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_notification_agent.py
"""Tests for the Notification Agent."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from src.agents import notification_agent as na


def _mock_llm(responses):
    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    llm = MagicMock()
    llm.bind_tools.return_value = llm_with_tools
    return llm


def test_preview_instruction_does_not_save_summary(monkeypatch):
    generate_summary_mock = MagicMock()
    monkeypatch.setattr(na, "generate_summary_tool", generate_summary_mock)

    llm = _mock_llm([AIMessage(content="### Ticket Preview\nConfirm?")])

    result = na.run_notification_agent(
        llm, "alice@company.com",
        instruction="Preview the ticket details and ask for confirmation.",
        context="Issue: VPN Connection, Device: Company Laptop, Warranty: ACTIVE",
    )

    assert "Confirm?" in result
    generate_summary_mock.assert_not_called()


def test_confirmed_instruction_saves_summary(monkeypatch):
    generate_summary_mock = MagicMock(
        return_value={"status": "success", "summary_id": "sum-1", "message": "Summary sum-1 saved."}
    )
    monkeypatch.setattr(na, "generate_summary_tool", generate_summary_mock)

    responses = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": "generate_summary",
                "args": {"summary": "Ticket tkt-1 created for VPN issue.", "ticket_id": "tkt-1"},
                "id": "1",
            }],
        ),
        AIMessage(content="All done, summary saved."),
    ]
    llm = _mock_llm(responses)

    result = na.run_notification_agent(
        llm, "alice@company.com",
        instruction="The user confirmed and the ticket is created. Generate the summary.",
        context="Ticket ID: tkt-1",
    )

    assert "summary saved" in result
    generate_summary_mock.assert_called_once_with(
        "alice@company.com", "Ticket tkt-1 created for VPN issue.", "tkt-1"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_notification_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.notification_agent'`

- [ ] **Step 3: Write the implementation**

```python
# src/agents/notification_agent.py
"""Notification Agent: presents ticket details, asks for confirmation, and saves summaries."""

from langchain_core.tools import tool

from src.agents.agent_loop import run_tool_calling_loop
from src.tools.summary_tools import generate_summary_tool

NOTIFICATION_SYSTEM_PROMPT = """You are the Notification Agent, part of TechAssist AI's \
support workflow. You are given an instruction and context describing what happened so far.

- If the instruction asks you to preview ticket details and ask for confirmation, write a \
clear preview (issue, device, warranty status, proposed ticket) and end with a question \
asking the user to confirm. Do NOT call generate_summary in this case.
- If the instruction says the user confirmed and/or the ticket has been created, call \
generate_summary(summary, ticket_id) with a concise summary of the interaction, then tell \
the user it has been saved.
"""


def _build_tools(user_email: str) -> list:
    @tool
    def generate_summary(summary: str, ticket_id: str = None) -> str:
        """Save a summary of this support interaction. Only call after the ticket has been created and the user confirmed."""
        result = generate_summary_tool(user_email, summary, ticket_id)
        return result["message"]

    return [generate_summary]


def run_notification_agent(llm, user_email: str, instruction: str, context: str = "") -> str:
    """Run the Notification Agent for one delegated task."""
    tools = _build_tools(user_email)
    messages = [("user", f"Instruction: {instruction}\n\nContext:\n{context}")]
    result = run_tool_calling_loop(llm, tools, NOTIFICATION_SYSTEM_PROMPT, messages)
    return result["text"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_notification_agent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/notification_agent.py tests/test_notification_agent.py
git commit -m "feat: add Notification Agent"
```

---

### Task 8: Supervisor Agent

**Files:**
- Create: `src/agents/supervisor_agent.py`
- Test: `tests/test_supervisor_agent.py`

**Interfaces:**
- Consumes: `build_helpdesk_tools`, `rag_retriever` from `src/agents/unified_agent.py` (Task 5); `run_tool_calling_loop` (Task 1); `analyze_request`, `RequestAnalysis` (Task 2); `run_asset_support_agent` (Task 6); `run_notification_agent` (Task 7).
- Produces: `SupervisorAgent(user_email, user_role="employee", temperature=0.0, model_name=None, provider="google", employee_id=None)` with `.invoke(user_input: str) -> str` and attributes `last_tools_used`, `last_rag_used`, `agent_name`, `model_name`, `provider_label`, `last_token_usage` — the same public surface `app.py` reads from `TechAssistAgent` today.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_supervisor_agent.py
"""Integration test for SupervisorAgent's confirm-before-ticket-creation flow."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

from src.agents import asset_support_agent as asa
from src.agents import notification_agent as na
from src.agents.request_analysis_agent import RequestAnalysis
from src.agents.supervisor_agent import SupervisorAgent


def _tool_call_message(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def test_ticket_is_only_created_after_explicit_confirmation(monkeypatch):
    create_ticket_mock = MagicMock(
        return_value={"status": "success", "ticket_id": "tkt-1", "message": "Ticket tkt-1 created successfully."}
    )
    generate_summary_mock = MagicMock(
        return_value={"status": "success", "summary_id": "sum-1", "message": "Summary sum-1 saved."}
    )
    monkeypatch.setattr(asa, "create_ticket_tool", create_ticket_mock)
    monkeypatch.setattr(na, "generate_summary_tool", generate_summary_mock)

    responses = [
        # --- Turn 1: analyze, look up asset + warranty, preview, wait ---
        _tool_call_message("analyze_support_request", {"user_message": "VPN issue"}, "t1"),
        _tool_call_message(
            "asset_and_ticket_support",
            {
                "instruction": "Look up the asset and check warranty. Do not create a ticket yet.",
                "context": "Issue: VPN Connection, Device: Company Laptop",
            },
            "t2",
        ),
        _tool_call_message("search_asset", {"query": "Alice Johnson"}, "a1"),
        _tool_call_message("check_warranty", {"query": "Alice Johnson"}, "a2"),
        AIMessage(content="Found MacBook Pro, warranty is active."),
        _tool_call_message(
            "notify_user",
            {
                "instruction": "Preview the ticket details and ask for confirmation.",
                "context": "Issue: VPN Connection, Device: Company Laptop, Warranty: ACTIVE",
            },
            "t3",
        ),
        AIMessage(content="### Ticket Preview\nShall I proceed? (yes/no)"),
        AIMessage(content="### Ticket Preview\nShall I proceed? (yes/no)"),
        # --- Turn 2: user confirmed, create ticket, summarize ---
        _tool_call_message(
            "asset_and_ticket_support",
            {
                "instruction": "The user confirmed. Create the ticket now.",
                "context": "Issue: VPN Connection, Device: Company Laptop",
            },
            "t4",
        ),
        _tool_call_message(
            "create_ticket",
            {"title": "VPN Connection Issue", "description": "Company laptop cannot connect to VPN"},
            "c1",
        ),
        AIMessage(content="Ticket tkt-1 created."),
        _tool_call_message(
            "notify_user",
            {
                "instruction": "The user confirmed and the ticket is created. Generate the summary.",
                "context": "Ticket ID: tkt-1",
            },
            "t5",
        ),
        _tool_call_message(
            "generate_summary",
            {
                "summary": "Created ticket tkt-1 for a VPN connection issue on the company laptop.",
                "ticket_id": "tkt-1",
            },
            "g1",
        ),
        AIMessage(content="All done! Summary saved."),
        AIMessage(content="Ticket tkt-1 created and summary saved. Thanks!"),
    ]

    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = llm_with_tools
    mock_llm.with_structured_output.return_value.invoke.return_value = RequestAnalysis(
        issue="VPN Connection", device="Company Laptop", action="Create Ticket"
    )

    monkeypatch.setattr(
        SupervisorAgent,
        "_build_llm",
        lambda self, provider, model_name, temperature: (mock_llm, "gemini-3.5-flash-lite"),
    )

    supervisor = SupervisorAgent("alice.johnson@techassist.com", "employee", employee_id="EMP001")

    turn1_reply = supervisor.invoke(
        "My laptop isn't connecting to the company VPN. Create a ticket and check if my warranty is active."
    )
    assert "proceed" in turn1_reply.lower()
    create_ticket_mock.assert_not_called()

    turn2_reply = supervisor.invoke("Yes, go ahead.")
    assert "tkt-1" in turn2_reply
    create_ticket_mock.assert_called_once_with(
        "alice.johnson@techassist.com", "VPN Connection Issue", "Company laptop cannot connect to VPN"
    )
    generate_summary_mock.assert_called_once_with(
        "alice.johnson@techassist.com",
        "Created ticket tkt-1 for a VPN connection issue on the company laptop.",
        "tkt-1",
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_supervisor_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.supervisor_agent'`

- [ ] **Step 3: Write the implementation**

```python
# src/agents/supervisor_agent.py
"""SupervisorAgent: orchestrates Request Analysis, Asset & Support, and Notification
agents as tools, alongside all Phase 2 helpdesk tools."""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory

from src.agents.unified_agent import build_helpdesk_tools, rag_retriever
from src.agents.agent_loop import run_tool_calling_loop
from src.agents.request_analysis_agent import analyze_request
from src.agents.asset_support_agent import run_asset_support_agent
from src.agents.notification_agent import run_notification_agent


class SupervisorAgent:
    """
    Multi-agent IT support supervisor.

    Wraps the Request Analysis, Asset & Support, and Notification agents as tools
    alongside all Phase 2 helpdesk tools (tickets, password, software, unlock, KB search).
    """

    PROVIDER_LABELS = {"google": "Google Gemini", "huggingface": "HuggingFace"}

    def __init__(
        self,
        user_email: str,
        user_role: str = "employee",
        temperature: float = 0.0,
        model_name: str = None,
        provider: str = "google",
        employee_id: str = None,
    ):
        self.user_email = user_email
        self.user_role = user_role
        self.employee_id = employee_id
        self.temperature = temperature
        self.provider = provider
        self.provider_label = self.PROVIDER_LABELS.get(provider, provider)
        self.agent_name = "TechAssist Supervisor Agent (Multi-Agent)"
        self.last_tools_used = []
        self.last_rag_used = []
        self.last_token_usage = None

        self.llm, self.model_name = self._build_llm(provider, model_name, temperature)
        self.memory = InMemoryChatMessageHistory()
        self.tools = self._define_tools()

    def _build_llm(self, provider: str, model_name: str, temperature: float):
        """Build the chat model for the selected provider. Returns (llm, resolved_model_name)."""
        if provider == "huggingface":
            repo_id = model_name or os.getenv(
                "HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"
            )
            endpoint = HuggingFaceEndpoint(repo_id=repo_id, temperature=temperature or 0.01)
            return ChatHuggingFace(llm=endpoint), repo_id

        if provider != "google":
            raise ValueError(f"Unknown provider: {provider}")

        resolved_model = model_name or "gemini-3.5-flash-lite"
        return ChatGoogleGenerativeAI(model=resolved_model, temperature=temperature), resolved_model

    def _define_tools(self) -> list:
        base_tools = build_helpdesk_tools(self.user_email, self.user_role, self.employee_id, rag_retriever)

        user_email = self.user_email
        employee_id = self.employee_id
        is_admin = self.user_role == "admin"
        llm = self.llm

        @tool
        def analyze_support_request(user_message: str) -> str:
            """Extract issue type, device, and required action from a free-form IT
            support request. Call this first for new device/VPN/hardware issues before
            looking anything up."""
            result = analyze_request(llm, user_message)
            return result.model_dump_json()

        @tool
        def asset_and_ticket_support(instruction: str, context: str = "") -> str:
            """Delegate to the Asset & Support Agent to search assets, check warranty,
            or create a support ticket. `instruction` tells it what to do right now
            (e.g. 'look up the asset and check warranty, do not create a ticket yet'
            or 'the user confirmed, create the ticket now'). `context` carries the
            relevant details gathered so far (issue, device, prior findings)."""
            return run_asset_support_agent(llm, user_email, employee_id, is_admin, instruction, context)

        @tool
        def notify_user(instruction: str, context: str = "") -> str:
            """Delegate to the Notification Agent to present ticket details and ask
            for confirmation, or to generate and save a final support summary.
            `instruction` e.g. 'preview these ticket details and ask for confirmation'
            or 'the user confirmed and the ticket is created, generate the summary'.
            `context` carries the relevant details to present or summarize."""
            return run_notification_agent(llm, user_email, instruction, context)

        return base_tools + [analyze_support_request, asset_and_ticket_support, notify_user]

    def _create_system_prompt(self) -> str:
        admin_line = (
            "ADMIN-ONLY: list_pending_software_requests, approve_software_request, "
            "reject_software_request, unlock_account, list_password_reset_requests"
            if self.user_role == "admin"
            else "ADMIN-ONLY tools are not available to your role."
        )
        return f"""You are TechAssist, a professional IT Support Assistant for TechAssist \
Solutions, acting as a Supervisor over specialized agents.

==== YOUR IDENTITY ====
- User Email: {self.user_email}
- User Role: {self.user_role}

==== RESPONSE FORMAT ====
Always format your responses using markdown: **bold** for key info, `code` for IDs, \
bullet/numbered lists, ### headers for sections, > for notes, tables for structured data.

==== MULTI-AGENT WORKFLOW (device/VPN/hardware issues) ====
For requests that describe a device problem, possibly needing a ticket and/or a warranty
check (e.g. "my laptop won't connect to VPN, create a ticket and check my warranty"):

1. Call analyze_support_request(user_message) to extract issue/device/action.
2. If a ticket may be needed, call asset_and_ticket_support with an instruction to look
   up the asset and check warranty ONLY — do not ask it to create a ticket yet.
3. Call notify_user with an instruction to preview the proposed ticket (issue, device,
   warranty status) and ask the user to confirm. Then STOP and wait for the user's reply
   — do NOT create the ticket in this turn.
4. Only on a later turn, once the user has explicitly confirmed (e.g. "yes", "go ahead"),
   call asset_and_ticket_support again with an instruction stating the user confirmed and
   to create the ticket now, using the issue/device from step 1-2 as context.
5. Then call notify_user with an instruction to generate and save the summary, and present
   the final confirmation (ticket ID + summary) to the user.

HARD RULE: never let a ticket be created in the same turn as its preview. Always wait for
a separate, explicit user confirmation message first.

==== OTHER CAPABILITIES (tools) ====
TICKET MANAGEMENT: create_ticket, check_ticket_status, list_my_tickets, close_ticket
PASSWORD: reset_password (confirm with user first)
SOFTWARE REQUESTS: request_software, check_software_request_status, list_my_software_requests
ASSET LOOKUP: lookup_assets(query, asset_type)
KNOWLEDGE BASE: search_knowledge_base(query)
{admin_line}

For reset_password, create_ticket (direct tool), and request_software: NEVER call the
tool in the same turn where you present its preview. Always show the template first and
wait for a separate follow-up confirmation.

==== ACCESS CONTROL ====
All operations are automatically scoped to {self.user_email}. Employees can only manage
their own tickets and requests; admins can view/approve requests from all users.

Always prioritize user needs while maintaining security and access control."""

    def invoke(self, user_input: str) -> str:
        """Run the supervisor with user input and return the response text."""
        self.memory.add_user_message(user_input)
        history = self.memory.messages

        messages = []
        for msg in history[:-1]:
            if isinstance(msg, HumanMessage):
                messages.append(("user", msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(("assistant", msg.content))
        messages.append(("user", user_input))

        result = run_tool_calling_loop(
            self.llm, self.tools, self._create_system_prompt(), messages, max_iterations=6
        )
        response_text = result["text"]
        tool_calls_made = result["tool_calls"]

        self.last_tools_used = [
            tc["name"] for tc in tool_calls_made if tc["name"] != "search_knowledge_base"
        ]
        self.last_rag_used = [
            tc["args"].get("query") for tc in tool_calls_made if tc["name"] == "search_knowledge_base"
        ]
        self.last_token_usage = result["token_usage"]

        self.memory.add_ai_message(response_text)
        return response_text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_supervisor_agent.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Run the full test suite**

Run: `venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS — all tests (Phase 2 regression suite + all new Phase 3 tests) pass.

- [ ] **Step 6: Commit**

```bash
git add src/agents/supervisor_agent.py tests/test_supervisor_agent.py
git commit -m "feat: add Supervisor Agent orchestrating Phase 3 sub-agents"
```

---

### Task 9: Wire the Supervisor into the app

**Files:**
- Modify: `src/conversation.py`

**Interfaces:**
- Consumes: `SupervisorAgent` from Task 8.
- `get_agent_instance(...)` return type changes from `TechAssistAgent` to `SupervisorAgent`; call signature is unchanged, so `app.py` needs no edits.

- [ ] **Step 1: Update `src/conversation.py`**

Replace its full contents with:

```python
"""Conversation handler using the multi-agent Supervisor."""

from src.agents.supervisor_agent import SupervisorAgent
from src.prompts import get_available_roles


def get_agent_instance(
    user_email: str,
    role: str,
    temperature: float = 0.0,
    provider: str = "google",
    employee_id: str = None,
) -> SupervisorAgent:
    """Get a SupervisorAgent instance.

    Args:
        user_email: User's email
        role: "employee", "engineer", or "admin"
        temperature: LLM temperature (0.0 - 2.0)
        provider: LLM provider, "google" or "huggingface"
        employee_id: User's employee ID, used to scope asset lookups

    Returns:
        SupervisorAgent instance with memory
    """
    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    return SupervisorAgent(user_email, role, temperature, provider=provider, employee_id=employee_id)
```

- [ ] **Step 2: Run the full test suite**

Run: `venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS — no test imports `get_agent_instance` directly today, so this is a
regression check that nothing else broke.

- [ ] **Step 3: Commit**

```bash
git add src/conversation.py
git commit -m "feat: wire Supervisor Agent into the main chat"
```

- [ ] **Step 4: Manual smoke test in the running app**

Run: `streamlit run app.py` (or use the project's preview tooling), log in as
`alice@techassist.com` / `password123`, and in the chat send:

> My laptop isn't connecting to the company VPN. Create a ticket and check if my
> laptop warranty is still active.

Confirm the assistant analyzes the request, looks up the asset/warranty, and presents
a ticket preview asking for confirmation **without** creating a ticket yet. Reply "yes"
and confirm it then creates the ticket and reports a summary. Also spot-check that
password reset and software request flows (Phase 2 features) still work unchanged.
