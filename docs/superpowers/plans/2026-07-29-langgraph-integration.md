# LangGraph Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `SupervisorAgent`'s hand-rolled tool-calling loop with a real LangGraph graph (`langgraph.prebuilt.create_react_agent`), with zero behavior change to tools, prompts, memory, or the progress-callback/tooltip mechanism.

**Architecture:** `SupervisorAgent` currently drives `run_tool_calling_loop()` — a manual `for` loop that calls `llm.bind_tools(tools)`, executes returned tool calls, appends `ToolMessage`s, and repeats. This plan swaps only that loop for a compiled LangGraph ReAct graph built once in `__init__` via `create_react_agent(llm, tools, prompt=system_prompt)`. The graph is invoked statelessly each turn — the full message history is still passed in from `self.memory` exactly as today, so no checkpointer is introduced and no cross-turn behavior changes. The three delegation tools (`analyze_support_request`, `asset_and_ticket_support`, `notify_user`) are untouched, so the progress callback and the two sub-agents (`asset_support_agent.py`, `notification_agent.py`, both still built on `agent_loop.run_tool_calling_loop`) are unaffected. `agent_loop.py` stays exactly as-is — it keeps serving the two sub-agents; only the Supervisor's own loop moves to LangGraph.

**Tech Stack:** `langgraph` (new dependency), `langchain_core.messages`, existing `langchain_google_genai` / `langchain_huggingface` chat models.

## Global Constraints

- Do not add a `langgraph` checkpointer (e.g. `MemorySaver`) — conversation memory stays exactly as-is, owned by `SupervisorAgent.memory` (`InMemoryChatMessageHistory`). Adding graph-native persistence is out of scope (YAGNI — it would duplicate the existing memory system).
- Do not touch `src/agents/agent_loop.py`, `src/agents/asset_support_agent.py`, or `src/agents/notification_agent.py`. They are unaffected by this change.
- Do not change any tool signature, the system prompt text, or `AGENT_TOOL_LABELS`.
- Preserve exact existing public behavior of `SupervisorAgent.invoke()`: same return value, same `last_tools_used` / `last_rag_used` / `last_token_usage` / `last_agents_used` semantics, same `on_progress` callback timing.
- Both existing tests in `tests/test_supervisor_agent.py` must pass unmodified if at all possible; only touch them if the graph's message-passing shape genuinely requires it (see Task 3).

---

### Task 1: Add the `langgraph` dependency

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `langgraph` importable (`from langgraph.prebuilt import create_react_agent`) for Task 2.

- [ ] **Step 1: Add the dependency**

Add this line to `requirements.txt`, after the existing `langchain-mcp-adapters` line:

```
langgraph>=0.2.0
```

- [ ] **Step 2: Install it**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: Verify the import works**

Run: `python -c "from langgraph.prebuilt import create_react_agent; print('ok')"`
Expected: prints `ok` with no `ImportError`.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add langgraph dependency"
```

---

### Task 2: Replace the Supervisor's manual loop with a compiled LangGraph graph

> **Correction (during implementation):** the installed `langgraph` version
> (pulled in by Task 1's `langgraph>=0.2.0` floor) resolved to 1.2.10, where
> `langgraph.prebuilt.create_react_agent` is deprecated and internally
> delegates to `langchain.agents.create_agent`'s middleware pipeline, which
> does not call the model via a plain `model.bind_tools(tools).invoke(...)`
> — it breaks both the existing tests' mocking contract and, more
> importantly, is simply the wrong tool now. Steps 2 and 3 below use a
> hand-built two-node `StateGraph` instead (`agent` node calls
> `self.llm_with_tools.invoke(...)` directly, `tools` node is a plain
> `ToolNode`), which preserves the exact `bind_tools(tools)` → `invoke(...)`
> call shape the old loop and the tests already assume.

**Files:**
- Modify: `src/agents/supervisor_agent.py`
- Test: `tests/test_supervisor_agent.py` (verification only — see Task 3 if it needs changes)

**Interfaces:**
- Consumes: `langgraph.prebuilt.create_react_agent(model, tools, *, prompt=None)` → compiled graph with `.invoke({"messages": [...]}, config=...) -> {"messages": [...]}`.
- Consumes: `agent_loop.extract_text`, `agent_loop._extract_usage`, `agent_loop._sum_usage` (already defined in `src/agents/agent_loop.py:7-50` — import and reuse, do not duplicate).
- Produces: `SupervisorAgent.invoke()` keeps its existing signature and return type (`str`), and keeps setting `self.last_tools_used`, `self.last_rag_used`, `self.last_token_usage`, `self.last_agents_used` exactly as before.

- [ ] **Step 1: Import what's needed**

At the top of `src/agents/supervisor_agent.py`, add these imports alongside the existing ones (after line 15 `from src.agents.notification_agent import run_notification_agent`):

```python
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.errors import GraphRecursionError
from src.agents.agent_loop import extract_text, _extract_usage, _sum_usage
```

- [ ] **Step 2: Build the graph once in `__init__`**

In `__init__` (`src/agents/supervisor_agent.py:33-57`), the last two lines currently read:

```python
        self.llm, self.model_name = self._build_llm(provider, model_name, temperature)
        self.memory = InMemoryChatMessageHistory()
        self.tools = self._define_tools()
```

Replace them with:

```python
        self.llm, self.model_name = self._build_llm(provider, model_name, temperature)
        self.memory = InMemoryChatMessageHistory()
        self.tools = self._define_tools()
        self.max_iterations = 6
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.graph = self._build_graph()
```

`_create_system_prompt()` only depends on `self.user_email`, `self.user_role`, both already set above this point.

Add this method to `SupervisorAgent`, right above `invoke()` (`src/agents/supervisor_agent.py:188`):

```python
    def _build_graph(self):
        """Two-node LangGraph loop equivalent to the old run_tool_calling_loop:
        an `agent` node calls the (already tool-bound) LLM, a `tools` node
        executes any tool calls, looping until the model stops calling tools."""
        system_prompt = self._create_system_prompt()

        def call_model(state):
            response = self.llm_with_tools.invoke([SystemMessage(system_prompt)] + state["messages"])
            return {"messages": [response]}

        graph = StateGraph(MessagesState)
        graph.add_node("agent", call_model)
        graph.add_node("tools", ToolNode(self.tools))
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
        return graph.compile()
```

- [ ] **Step 3: Replace the loop call in `invoke()`**

In `invoke()` (`src/agents/supervisor_agent.py:188-232`), this block currently reads:

```python
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
```

Replace it with:

```python
        input_messages = self._to_base_messages(messages)
        try:
            graph_result = self.graph.invoke(
                {"messages": input_messages},
                config={"recursion_limit": 2 * self.max_iterations + 1},
            )
            new_messages = graph_result["messages"][len(input_messages):]
        except GraphRecursionError:
            # Iteration cap hit while the model still wanted to call a tool —
            # same fallback agent_loop.run_tool_calling_loop uses: one more
            # plain (non-tool-bound) call so the model returns natural-language
            # text instead of leaving the turn empty.
            state = self.graph.get_state({"configurable": {"thread_id": "n/a"}})
            new_messages = []

        tool_calls_made = [
            {"name": tc["name"], "args": tc["args"]}
            for msg in new_messages
            if isinstance(msg, AIMessage)
            for tc in (msg.tool_calls or [])
        ]

        last_ai_message = next(
            (m for m in reversed(new_messages) if isinstance(m, AIMessage)), None
        )
        if last_ai_message is not None and not last_ai_message.tool_calls:
            response_text = extract_text(last_ai_message)
        else:
            # No clean final text (recursion cap, or the graph's last message
            # still carries tool_calls) — force one plain call for a summary.
            fallback = self.llm.invoke([SystemMessage(self._create_system_prompt())] + input_messages + new_messages)
            response_text = extract_text(fallback)

        self.last_tools_used = [
            tc["name"] for tc in tool_calls_made if tc["name"] != "search_knowledge_base"
        ]
        self.last_rag_used = [
            tc["args"].get("query") for tc in tool_calls_made if tc["name"] == "search_knowledge_base"
        ]
        self.last_token_usage = _sum_usage([_extract_usage(m) for m in new_messages if isinstance(m, AIMessage)])
```

Add `SystemMessage` to the existing `langchain_core.messages` import at the top of the file (`src/agents/supervisor_agent.py:8`), changing:

```python
from langchain_core.messages import HumanMessage, AIMessage
```

to:

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
```

- [ ] **Step 4: Add the `_to_base_messages` helper**

`create_react_agent`'s graph expects `BaseMessage` instances (or a plain string), not the `(role, content)` tuples `run_tool_calling_loop` accepted. Add this method to `SupervisorAgent`, right above `invoke()` (`src/agents/supervisor_agent.py:188`):

```python
    def _to_base_messages(self, messages: list) -> list:
        """Convert (role, content) tuples to BaseMessage instances for the graph."""
        converted = []
        for msg in messages:
            if isinstance(msg, tuple):
                role, content = msg
                converted.append(HumanMessage(content) if role == "user" else AIMessage(content))
            else:
                converted.append(msg)
        return converted
```

- [ ] **Step 5: Remove the now-unused import**

`run_tool_calling_loop` is no longer called from this file. Remove this line (`src/agents/supervisor_agent.py:12`):

```python
from src.agents.agent_loop import run_tool_calling_loop
```

(already replaced by the `extract_text, _extract_usage, _sum_usage` import from Step 1).

- [ ] **Step 6: Run the existing tests**

Run: `pytest tests/test_supervisor_agent.py -v`
Expected: both tests pass. If either fails, read the assertion diff carefully before changing test code — see Task 3 for what's allowed to change and why.

- [ ] **Step 7: Commit**

```bash
git add src/agents/supervisor_agent.py
git commit -m "feat: run SupervisorAgent's tool-calling loop through LangGraph"
```

---

### Task 3: Reconcile test mocking with the graph's message-passing shape

**Files:**
- Modify: `tests/test_supervisor_agent.py` (only if Task 2's test run fails)

**Interfaces:**
- Consumes: `SupervisorAgent` as changed in Task 2.

This task is conditional — only do this if `pytest tests/test_supervisor_agent.py -v` from Task 2 Step 6 fails.

- [ ] **Step 1: Diagnose the specific failure**

Both tests mock at the same seam Task 2 preserves: `mock_llm.bind_tools.return_value = llm_with_tools` and `llm_with_tools.invoke.side_effect = responses`. `create_react_agent(self.llm, self.tools, ...)` calls `self.llm.bind_tools(self.tools)` once when the graph is built (in `__init__`), then the graph's internal agent node calls `llm_with_tools.invoke(...)` once per iteration — the same call shape the old `run_tool_calling_loop` used. If a test fails, it is most likely one of:

- **Recursion limit units mismatch**: LangGraph's `recursion_limit` counts graph *steps* (each agent-node visit AND each tools-node visit counts as one step), not LLM calls. `2 * self.max_iterations + 1` in Task 2 Step 3 approximates this, but if `test_ticket_is_only_created_after_explicit_confirmation`'s turn 1 (5 LLM calls: t1, t2, then the nested sub-agent calls don't count against the Supervisor's own graph, then t3, then 2 plain-text AIMessages) hits the cap unexpectedly, raise the limit — e.g. `4 * self.max_iterations + 1` — rather than restructuring the test.
- **`SystemMessage` duplication**: `create_react_agent`'s `prompt=` already injects the system prompt once per graph invocation. Confirm `input_messages` (from `_to_base_messages`) does NOT itself contain a `SystemMessage` — it shouldn't, since `messages` built in `invoke()` (`src/agents/supervisor_agent.py:202-208`) only ever contains `("user", ...)` / `("assistant", ...)` tuples.

- [ ] **Step 2: Fix forward, not backward**

If a genuine behavior gap is found (not a units/shape mismatch), fix `supervisor_agent.py`, not the test — the test encodes the two-turn confirmation contract from the "HARD RULE" in the system prompt (`src/agents/supervisor_agent.py:156`), which this plan's Global Constraints require preserving unchanged.

- [ ] **Step 3: Re-run and commit if changed**

```bash
pytest tests/test_supervisor_agent.py -v
git add tests/test_supervisor_agent.py
git commit -m "test: adjust supervisor test mocking for LangGraph recursion semantics"
```

(Skip the commit if no test file changes were needed.)

---

### Task 4: Update the architecture doc

**Files:**
- Modify: `docs/implementation/agent_workflow.md`

**Interfaces:**
- None — documentation only.

- [ ] **Step 1: Correct the "How the chain works" section**

In `docs/implementation/agent_workflow.md`, replace the sentence (currently reading "The Supervisor is not a separate router process — it's a single LLM with function-calling...") to note that the Supervisor's own agent↔tools loop is now a compiled LangGraph `create_react_agent` graph (built in `SupervisorAgent.__init__`), while the two sub-agents (Asset & Support, Notification) still run their own independent instance of the hand-rolled `run_tool_calling_loop` from `agent_loop.py` — unchanged by this plan.

- [ ] **Step 2: Commit**

```bash
git add docs/implementation/agent_workflow.md
git commit -m "docs: reflect LangGraph-backed Supervisor loop"
```
