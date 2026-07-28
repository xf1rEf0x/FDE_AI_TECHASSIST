# Phase 3: Multi-Agent Supervisor Architecture — Design

Date: 2026-07-28
Status: Approved for planning

## Goal

Implement `docs/implementation/phase_3.md`: a Supervisor agent that orchestrates three
specialized agents — Request Analysis, Asset & Support, Notification — exposed to the
Supervisor as LangChain tools. The Supervisor replaces `TechAssistAgent` as the main
chat driver, keeping all existing Phase 2 capabilities.

## Architecture

One `SupervisorAgent` runs a multi-round tool-calling loop per user turn. Its tool list is:

- All existing Phase 2 tools (tickets, password reset, software requests, account unlock,
  KB search) — reused unchanged.
- Three new tools, each delegating to one sub-agent:
  - `analyze_support_request(user_message)` → Request Analysis Agent
  - `asset_and_ticket_support(instruction, context)` → Asset & Support Agent
  - `notify_user(instruction, context)` → Notification Agent

The Supervisor's LLM decides when to call these based on conversation context — this is
not a hardcoded pipeline. `instruction`/`context` strings are how the Supervisor passes
what it wants a sub-agent to do and what it already knows (e.g. "look up the asset and
check warranty, do not create a ticket yet").

## Shared tool-calling loop

`unified_agent.py`'s current `invoke()` only executes one round of tool calls per turn.
The Supervisor and both non-trivial sub-agents (Asset & Support, Notification) need
multiple rounds within a single call (e.g. search asset → check warranty, using the
first result). Rather than duplicating that loop three times, a single shared helper:

`src/agents/agent_loop.py`
```python
def run_tool_calling_loop(llm, tools, system_prompt, messages, max_iterations=5) -> tuple[str, list[str]]:
    """Bind tools, run the model, execute any tool_calls, feed results back as
    ToolMessages, and repeat until the model stops calling tools or max_iterations
    is hit. Returns (final_text, tool_names_called_in_order)."""
```

implements this once. `unified_agent.py` is not changed to use this loop — it keeps its
existing one-round behavior, which is out of scope here.

## Components

### 1. Request Analysis Agent (`src/agents/request_analysis_agent.py`)

No tools — a single structured-output LLM call.

```python
class RequestAnalysis(BaseModel):
    issue: str
    device: str
    action: str

def analyze_request(llm, user_message: str) -> RequestAnalysis:
    return llm.with_structured_output(RequestAnalysis).invoke(
        f"Extract the issue type, device, and required action from this IT support "
        f"request:\n{user_message}"
    )
```

Exposed to the Supervisor as `analyze_support_request(user_message) -> str` (JSON via
`model_dump_json()`).

### 2. Asset & Support Agent (`src/agents/asset_support_agent.py`)

A tool-calling loop (via `run_tool_calling_loop`) over 3 tools, built per-call as closures
scoped to `user_email`, `employee_id`, `is_admin` (same closure pattern as
`unified_agent.py` today):

- `search_asset(query, asset_type=None)` — reuses `search_employee_assets`
  (`src/tools/asset_search_tool.py`), unchanged.
- `check_warranty(query)` — **new** (`src/tools/warranty_tools.py`). Reuses
  `search_assets_by_employee`/`search_assets_by_serial` to find the asset(s), then
  compares each asset's `warranty_end` or `expiry_date` against `date.today()`
  (stdlib `datetime`) to report ACTIVE/EXPIRED per asset.
- `create_ticket(title, description)` — reuses `create_ticket_tool`
  (`src/tools/ticket_tools.py`), unchanged.

System prompt hard rule: **never call `create_ticket` unless the instruction explicitly
states the user has confirmed.** The Supervisor controls this via what it puts in
`instruction` — first call asks for lookup only, a later call (after user confirmation)
asks it to create the ticket.

Entry point: `run_asset_support_agent(user_email, employee_id, is_admin, instruction, context) -> str`.

### 3. Notification Agent (`src/agents/notification_agent.py`)

A tool-calling loop over 1 tool:

- `generate_summary(summary, ticket_id=None)` — **new**
  (`src/tools/summary_tools.py` + `src/storage/summary_store.py`). `SummaryStore`
  mirrors `TicketStore`'s shape (JSON file, `data/support_summaries.json`, created
  on first use) but stores summary records instead of tickets.

When asked to "preview" ticket details and ask for confirmation, the agent just composes
text — no tool call. When asked to "summarize" (after the ticket is created), it calls
`generate_summary`.

Entry point: `run_notification_agent(user_email, instruction, context) -> str`.

### 4. Supervisor Agent (`src/agents/supervisor_agent.py`)

- `__init__` mirrors `TechAssistAgent.__init__` (same LLM setup, same constructor
  signature: `user_email, user_role, temperature, model_name, provider, employee_id`).
- Tool list = `build_helpdesk_tools(user_email, user_role, employee_id, rag_retriever)`
  (extracted from `unified_agent.py`, see below) + the 3 new workflow tools defined above.
- `invoke(user_input)` appends to `InMemoryChatMessageHistory`, builds the message list,
  and calls `run_tool_calling_loop(...)` with `max_iterations=6`. Tracks `last_tools_used`
  (from the loop's returned tool names, excluding `search_knowledge_base` — same
  convention as today) and `last_rag_used`.
- Exposes the same public attributes `app.py` reads today: `invoke()`, `last_tools_used`,
  `last_rag_used`, `agent_name`, `model_name`, `provider_label`, `last_token_usage`.

### Refactor: `build_helpdesk_tools` extraction

`unified_agent.py`'s `_define_tools` method body moves to a module-level function
`build_helpdesk_tools(user_email, user_role, employee_id, rag_retriever) -> list`.
`TechAssistAgent._define_tools` becomes a one-line wrapper calling it. Behavior for
Phase 2 is unchanged — this only removes duplication so the Supervisor doesn't
reimplement ~200 lines of tool definitions.

## Confirmation flow (across chat turns)

Matches the pattern Phase 2 already uses for tickets/password resets — no new
mechanism, just conversation memory carrying state between turns:

1. User: "My laptop won't connect to VPN, create a ticket and check my warranty."
   Supervisor calls `analyze_support_request` → `asset_and_ticket_support`
   (instruction: lookup + warranty check only, no ticket) → `notify_user`
   (instruction: preview + ask for confirmation). Turn ends waiting for the user.
2. User: "yes, go ahead." Supervisor calls `asset_and_ticket_support` (instruction:
   user confirmed, create the ticket now — context includes the issue/device from
   step 1) → `notify_user` (instruction: summarize) → final message with ticket ID
   and summary confirmation.

## Wiring into the app

`src/conversation.py::get_agent_instance` returns `SupervisorAgent` instead of
`TechAssistAgent`. No changes needed to `app.py` since the public interface matches.

## New files

- `src/agents/agent_loop.py`
- `src/agents/request_analysis_agent.py`
- `src/agents/asset_support_agent.py`
- `src/agents/notification_agent.py`
- `src/agents/supervisor_agent.py`
- `src/tools/warranty_tools.py`
- `src/tools/summary_tools.py`
- `src/storage/summary_store.py`

## Edited files

- `src/agents/unified_agent.py` — extract `build_helpdesk_tools`, no behavior change.
- `src/conversation.py` — instantiate `SupervisorAgent`.

## Testing

- `check_warranty` date logic (active/expired/missing date) — pure function, easy
  fixture-based unit test.
- `SummaryStore` — save/list round-trip, mirrors existing `TicketStore` tests.
- `RequestAnalysis` structured output — mock `llm.with_structured_output(...).invoke`.
- `run_tool_calling_loop` — mock an LLM that calls a tool once then stops; verify it
  loops correctly and stops at `max_iterations`.
- Supervisor confirm-then-create-ticket flow — mock the LLM's tool-call decisions
  across two `invoke()` calls to verify `create_ticket` is not called before the
  second turn.
- Existing Phase 2 test suite must still pass unchanged after the `build_helpdesk_tools`
  extraction (regression check, not new tests).

## Out of scope

- Changing `unified_agent.py`'s own single-round tool-calling behavior.
- A dedicated LangGraph DAG (CLAUDE.md explicitly asks for simple sequential
  orchestration, not complex DAGs).
- UI changes beyond swapping which agent class powers the existing chat tab.
