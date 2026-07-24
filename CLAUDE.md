# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TechAssist AI is a multi-phase IT support assistant application being built for TechAssist Solutions (12,000 employees). The assistant evolves through four progressive phases, starting as a conversational chatbot and advancing to a deployable multi-agent system with real-world integrations.

**Tech Stack:**
- Backend: Python with Gemini API
- UI: Streamlit
- Agent Framework: LangChain + LangGraph
- ML: Structured output generation, tool calling

## Architecture Overview

### Four-Phase Evolution

**Phase 1: LLM Chatbot** (`docs/implementation/phase_1.md`)
- Simple conversational interface powered by Gemini API
- System prompts define IT support persona (different for employee/engineer/admin roles)
- Message history and session memory management
- Streamlit chat UI

**Phase 2: Single Agent with Tools** (`docs/implementation/phase_2.md`)
- Elevate Phase 1 chatbot into an agent using tool calling
- Tools: `asset_lookup()`, `password_reset_request()`, `create_ticket()`, `check_ticket_status()`, `software_request()`, `unlock_account()`
- Agent decides which tools to invoke based on natural language intent
- Human confirmation required before destructive actions (password resets)

**Phase 3: Multi-Agent System** (`docs/implementation/phase_3.md`)
- Three specialized agents with distinct responsibilities:
  1. **Request Analysis Agent** — Parse user input, extract issue type/device/action, return structured JSON
  2. **Asset & Support Agent** — Search employee assets (JSON file), check warranty, create tickets
  3. **Notification Agent** — Present results, confirm actions, generate summaries (save to JSON)
- Agents communicate via structured outputs; Phase 2 tools become Phase 3 data sources
- Workflow example: VPN issue → analyze request → lookup asset + warranty → create ticket → confirm → summarize

**Phase 4: Deployment** (`docs/implementation/phase_4.md`)
- Production-ready packaging: environment variables, .env config, logging
- Streamlit deployment setup
- Verify all three prior phases function end-to-end

### Key Design Decisions

- **Structured Output**: Agents use JSON-based structured outputs to ensure clean handoffs between phases (especially Phase 3 multi-agent)
- **Tool Mocking**: Early phases mock external services (asset lookup reads from JSON, ticket creation writes to JSON)
- **User Roles**: System prompts adapt responses based on user type (employee/engineer/admin) from Phase 1 onward
- **Human-in-the-Loop**: Confirm destructive actions before execution (Phase 2+)

## Development Workflow

### Project Structure (target)

```
fde_ai_1/
├── docs/                          # Phase requirements and context
│   ├── context.md                 # Client org, business challenges
│   └── implementation/
│       ├── phase_1.md
│       ├── phase_2.md
│       ├── phase_3.md
│       └── phase_4.md
├── src/                           # Application code
│   ├── agents/                    # LangChain agents (Phases 2–3)
│   ├── tools/                     # Tool implementations
│   ├── prompts/                   # System prompts by role
│   └── utils/                     # Shared utilities
├── data/                          # Mock data (assets, employees)
├── tests/                         # Unit + integration tests
├── app.py                         # Streamlit entry point
├── requirements.txt               # Python dependencies
├── .env.example                   # Template for environment variables
└── CLAUDE.md                      # This file
```

### Common Commands

Create `requirements.txt` (when project structure is ready):
```bash
pip install -r requirements.txt
```

Run Streamlit app:
```bash
streamlit run app.py
```

Run tests (when test suite exists):
```bash
pytest tests/
# Single test file:
pytest tests/test_agents.py
# Specific test:
pytest tests/test_agents.py::test_asset_lookup
```

Format and lint (recommended once codebase grows):
```bash
black src/ tests/
ruff check src/ tests/
```

### Development Notes

- **Gemini API**: Configured via `GOOGLE_API_KEY` environment variable (Phase 1+)
- **Structured Outputs**: Use Pydantic models or plain JSON schemas to define agent outputs; LangChain's `with_structured_output()` enforces schema validation
- **Testing Strategy**: Mock Gemini responses in early phases; use fixtures for mock asset data and tickets
- **Streaming**: Streamlit reruns on each interaction; maintain conversation state in `st.session_state`
- **Phase Progression**: Each phase builds on the prior one; refactoring Phase 1 chatbot into Phase 2 agent reuses prompts and session logic

## Client Context

See `docs/context.md` for business drivers:
- 12,000 employees, hybrid workforce
- Pain points: password resets, VPN access, software installation, laptop issues, account unlocks
- Exec goal: reduce helpdesk workload via AI automation

## Phase-Specific Implementation Notes

### Phase 1
- Focus: prompt quality and role-based system prompts
- No external APIs beyond Gemini
- Conversation memory: use LangChain `ConversationBufferMemory` or Streamlit session state

### Phase 2
- Convert Phase 1 prompts into tool-calling agent prompt
- Tools return structured data; agent decides invocation
- Implement confirmation flow for `password_reset_request()`

### Phase 3
- Request Analysis Agent output (JSON) feeds into Asset Agent input
- Asset Agent output feeds into Notification Agent
- Keep orchestration simple (sequential calls, not complex DAGs)

### Phase 4
- Move secrets to `.env`; load via `python-dotenv`
- Add basic logging (structlog or stdlib `logging`)
- Test deployment locally before pushing

## References

- Gemini API docs: https://ai.google.dev/
- LangChain: https://python.langchain.com/
- LangGraph: https://langchain-ai.github.io/langgraph/
- Streamlit: https://docs.streamlit.io/
