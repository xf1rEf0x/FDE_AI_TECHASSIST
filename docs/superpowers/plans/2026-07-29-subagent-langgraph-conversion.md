# Sub-Agent LangGraph Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the Asset & Support Agent and Notification Agent from the hand-rolled `run_tool_calling_loop` to the same hand-built two-node LangGraph `StateGraph` pattern already used by `SupervisorAgent` (see `docs/superpowers/plans/2026-07-29-langgraph-integration.md`), so their internal tool-calling steps become visible as nested spans in LangSmith trace views. This does NOT change the Studio canvas diagram (`langgraph dev`) — that only ever renders the top-level graph passed in `langgraph.json` (the Supervisor's), and sub-agents are still invoked as plain Python function calls from inside the Supervisor's `tools` node. Making them appear as their own boxes in the Studio canvas itself would require replacing the Supervisor's generic `ToolNode`/`tools_condition` with custom per-tool routing — out of scope, a materially bigger and riskier change the user explicitly declined for now.

**Architecture:** `asset_support_agent.py` and `notification_agent.py` each currently build a fresh tool list, then call `agent_loop.run_tool_calling_loop(llm, tools, system_prompt, messages)` and return `result["text"]`. This plan replaces that internal call in both files with a small compiled `StateGraph` (`agent` node + `tools` node via `ToolNode`/`tools_condition`), invoked once per call via `.stream(..., stream_mode="values")` — copying the exact pattern (and the two bugs already found and fixed in it) from `SupervisorAgent._build_graph()` / `SupervisorAgent.invoke()`:
- `max_concurrency: 1` in the graph config from the start (the Supervisor's final review caught this as a regression fixed after the fact — don't repeat that mistake here).
- Iterate via `graph.stream(..., stream_mode="values")` keeping `last_state`, so a `GraphRecursionError` doesn't silently discard the turn's tool-call results (again, learned the hard way on the Supervisor).

`request_analysis_agent.py` is NOT touched — `analyze_request()` is a single `llm.with_structured_output(...)` call with no tool-calling loop, nothing to convert.

`agent_loop.py`'s `run_tool_calling_loop` function itself is NOT removed or modified — it has its own direct unit tests (`tests/test_agent_loop.py`) validating it as a standalone utility, independent of who calls it. It becomes unused in production code after this plan, but deleting it is out of scope (unrelated cleanup, not requested).

**Tech Stack:** `langgraph` (already a dependency), same imports as `supervisor_agent.py`.

## Global Constraints

- Both sub-agents' public function signatures stay exactly the same: `run_asset_support_agent(llm, user_email, employee_id, is_admin, instruction, context="")` and `run_notification_agent(llm, user_email, instruction, context="")`, both still returning a plain `str`.
- Do not touch `src/agents/agent_loop.py`, `src/agents/request_analysis_agent.py`, `src/agents/supervisor_agent.py`, or any tool definitions inside `_build_tools()` in either file — only the loop-driving code changes.
- Do not touch `src/agents/unified_agent.py` or any Phase 2 tools.
- All four existing tests must pass unmodified: `tests/test_asset_support_agent.py` (2 tests), `tests/test_notification_agent.py` (2 tests), and both tests in `tests/test_supervisor_agent.py` (which mock the SAME shared `llm` object across the Supervisor's own graph AND whichever sub-agent graph runs inside a delegation tool call in that test — do not change the call shape `llm.bind_tools(tools)` → `.invoke(...)` that those mocks depend on).
- Use `config={"recursion_limit": 2 * max_iterations + 1, "max_concurrency": 1}` where `max_iterations` matches each function's current default (5, since neither `run_asset_support_agent` nor `run_notification_agent` currently overrides `run_tool_calling_loop`'s default `max_iterations=5`) — i.e. `recursion_limit=11`.
- Reuse `extract_text` from `src/agents/agent_loop.py` (already exists) rather than reimplementing it.

---

### Task 1: Convert the Asset & Support Agent to a LangGraph StateGraph

**Files:**
- Modify: `src/agents/asset_support_agent.py`
- Test: `tests/test_asset_support_agent.py` (verification only, should not need edits)

**Interfaces:**
- Consumes: `src.agents.agent_loop.extract_text` (existing).
- Produces: `run_asset_support_agent(...)` keeps its exact existing signature and `str` return type.

- [ ] **Step 1: Update imports**

At the top of `src/agents/asset_support_agent.py`, replace:

```python
from langgraph_core... # (whatever the current import line is for run_tool_calling_loop)
```

Concretely, replace this line:

```python
from src.agents.agent_loop import run_tool_calling_loop
```

with:

```python
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.errors import GraphRecursionError
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.agents.agent_loop import extract_text
```

- [ ] **Step 2: Replace `run_asset_support_agent`'s body**

Replace the current function body:

```python
def run_asset_support_agent(
    llm, user_email: str, employee_id: str, is_admin: bool, instruction: str, context: str = ""
) -> str:
    """Run the Asset & Support Agent for one delegated task."""
    tools = _build_tools(user_email, employee_id, is_admin)
    messages = [("user", f"Instruction: {instruction}\n\nContext:\n{context}")]
    result = run_tool_calling_loop(llm, tools, ASSET_SUPPORT_SYSTEM_PROMPT, messages)
    return result["text"]
```

with:

```python
def _build_graph(llm_with_tools, tools: list, system_prompt: str):
    """Two-node LangGraph loop (agent calls the tool-bound LLM, tools node
    executes any tool calls), mirroring SupervisorAgent._build_graph()."""

    def call_model(state):
        response = llm_with_tools.invoke([SystemMessage(system_prompt)] + state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def run_asset_support_agent(
    llm, user_email: str, employee_id: str, is_admin: bool, instruction: str, context: str = ""
) -> str:
    """Run the Asset & Support Agent for one delegated task."""
    tools = _build_tools(user_email, employee_id, is_admin)
    llm_with_tools = llm.bind_tools(tools)
    graph = _build_graph(llm_with_tools, tools, ASSET_SUPPORT_SYSTEM_PROMPT)

    input_messages = [HumanMessage(f"Instruction: {instruction}\n\nContext:\n{context}")]
    last_state = {"messages": input_messages}
    try:
        for last_state in graph.stream(
            {"messages": input_messages},
            config={"recursion_limit": 11, "max_concurrency": 1},
            stream_mode="values",
        ):
            pass
    except GraphRecursionError:
        pass

    final_messages = last_state["messages"]
    last_ai_message = next(
        (m for m in reversed(final_messages) if isinstance(m, AIMessage)), None
    )
    if last_ai_message is not None and not last_ai_message.tool_calls:
        return extract_text(last_ai_message)

    fallback = llm.invoke([SystemMessage(ASSET_SUPPORT_SYSTEM_PROMPT)] + final_messages)
    return extract_text(fallback)
```

- [ ] **Step 3: Run the existing tests**

Run: `pytest tests/test_asset_support_agent.py tests/test_supervisor_agent.py -v`
Expected: all 4 tests pass unmodified (2 in each file).

- [ ] **Step 4: Commit**

```bash
git add src/agents/asset_support_agent.py
git commit -m "feat: run Asset & Support Agent's tool-calling loop through LangGraph"
```

---

### Task 2: Convert the Notification Agent to a LangGraph StateGraph

**Files:**
- Modify: `src/agents/notification_agent.py`
- Test: `tests/test_notification_agent.py` (verification only, should not need edits)

**Interfaces:**
- Consumes: `src.agents.agent_loop.extract_text` (existing).
- Produces: `run_notification_agent(...)` keeps its exact existing signature and `str` return type.

- [ ] **Step 1: Update imports**

Replace this line in `src/agents/notification_agent.py`:

```python
from src.agents.agent_loop import run_tool_calling_loop
```

with:

```python
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.errors import GraphRecursionError
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.agents.agent_loop import extract_text
```

- [ ] **Step 2: Replace `run_notification_agent`'s body**

Replace the current function body:

```python
def run_notification_agent(llm, user_email: str, instruction: str, context: str = "") -> str:
    """Run the Notification Agent for one delegated task."""
    tools = _build_tools(user_email)
    messages = [("user", f"Instruction: {instruction}\n\nContext:\n{context}")]
    result = run_tool_calling_loop(llm, tools, NOTIFICATION_SYSTEM_PROMPT, messages)
    return result["text"]
```

with:

```python
def _build_graph(llm_with_tools, tools: list, system_prompt: str):
    """Two-node LangGraph loop (agent calls the tool-bound LLM, tools node
    executes any tool calls), mirroring SupervisorAgent._build_graph()."""

    def call_model(state):
        response = llm_with_tools.invoke([SystemMessage(system_prompt)] + state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def run_notification_agent(llm, user_email: str, instruction: str, context: str = "") -> str:
    """Run the Notification Agent for one delegated task."""
    tools = _build_tools(user_email)
    llm_with_tools = llm.bind_tools(tools)
    graph = _build_graph(llm_with_tools, tools, NOTIFICATION_SYSTEM_PROMPT)

    input_messages = [HumanMessage(f"Instruction: {instruction}\n\nContext:\n{context}")]
    last_state = {"messages": input_messages}
    try:
        for last_state in graph.stream(
            {"messages": input_messages},
            config={"recursion_limit": 11, "max_concurrency": 1},
            stream_mode="values",
        ):
            pass
    except GraphRecursionError:
        pass

    final_messages = last_state["messages"]
    last_ai_message = next(
        (m for m in reversed(final_messages) if isinstance(m, AIMessage)), None
    )
    if last_ai_message is not None and not last_ai_message.tool_calls:
        return extract_text(last_ai_message)

    fallback = llm.invoke([SystemMessage(NOTIFICATION_SYSTEM_PROMPT)] + final_messages)
    return extract_text(fallback)
```

- [ ] **Step 3: Run the existing tests**

Run: `pytest tests/test_notification_agent.py tests/test_supervisor_agent.py -v`
Expected: all 4 tests pass unmodified (2 in each file).

- [ ] **Step 4: Commit**

```bash
git add src/agents/notification_agent.py
git commit -m "feat: run Notification Agent's tool-calling loop through LangGraph"
```

---

### Task 3: Update docs to reflect all three loops now running through LangGraph

**Files:**
- Modify: `docs/implementation/agent_workflow.md`

**Interfaces:**
- None — documentation only.

- [ ] **Step 1: Correct the "How the chain works" section and the Agents table**

Update the description so it no longer says the two sub-agents "run their own independent instance of the hand-rolled `run_tool_calling_loop`" — instead, note that all three agents (Supervisor, Asset & Support, Notification) now each build and run their own small two-node LangGraph `StateGraph`, following the identical `agent`/`tools` node pattern. Keep the Request Analysis Agent's description unchanged (still a single structured-output call, no graph). Add a short note that `langgraph dev` / Studio (see `src/agents/studio_graph.py`, `langgraph.json`) only visualizes the Supervisor's top-level graph — sub-agent graphs run nested inside its `tools` node and are visible as nested spans in LangSmith trace views, not as boxes in the Studio canvas.

- [ ] **Step 2: Commit**

```bash
git add docs/implementation/agent_workflow.md
git commit -m "docs: reflect sub-agents also running through LangGraph"
```
