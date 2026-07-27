# LangChain Unification Design

**Date:** 2026-07-27  
**Objective:** Replace all agent implementations with a single pure LangChain unified agent (no LangGraph).

## Current State

Three separate agent classes:
- `HelpDeskAgent` (LangGraph-based)
- `SoftwareAgent` (custom implementation)
- `AssetAgent` (custom implementation)
- `IntentRouter` (dedicated routing logic)

Three separate conversation paths with manual intent detection.

## Target State

**Single `TechAssistAgent`** using pure LangChain:
- `AgentExecutor` with `ConversationBufferMemory`
- 6 tools: ticket creation/status/listing/closing, password reset, asset lookup, software request
- Agent decides which tool to invoke based on natural language intent (no explicit routing)
- Built-in memory eliminates manual history passing

## Architecture

### TechAssistAgent class

```python
class TechAssistAgent:
    def __init__(self, user_email: str, temperature: float = 0.0):
        self.llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=temperature)
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.tools = [create_ticket_tool, check_status_tool, ..., asset_lookup_tool]
        self.executor = AgentExecutor(agent=agent_chain, tools=self.tools, memory=self.memory)
    
    def invoke(self, user_input: str) -> str:
        result = self.executor.invoke({"input": user_input})
        return result["output"]
```

### Tools integration

All 6 tools scoped to `user_email` at definition time (no runtime scoping needed).

System prompt guides tool selection but agent chooses implicitly via tool calling.

## File changes

| File | Action |
|------|--------|
| `src/agents/helpdesk_agent.py` | Rewrite → `TechAssistAgent` with AgentExecutor |
| `src/agents/software_agent.py` | Delete |
| `src/asset_agent.py` | Delete |
| `src/intent_router.py` | Delete |
| `src/conversation.py` | Simplify → just instantiate agent, call invoke() |
| `app.py` | Update → use new agent in chat tab |
| `src/ui/helpdesk_tab.py` | Update → create agent instance, pass to tab |

## Data flow

```
User input (Streamlit)
  ↓
TechAssistAgent.invoke(user_input)
  ↓
AgentExecutor routes via tool calling
  ↓
Tool executes (agent pre-scoped to user_email)
  ↓
Memory auto-updates
  ↓
Response returned
```

## Implementation notes

- **Memory**: ConversationBufferMemory persists across chat turns in same session; new session = new agent instance
- **Tool scoping**: Each tool receives `user_email` at instantiation, no runtime checks needed
- **Streaming**: Use LangChain's `.stream()` method for token-by-token output to Streamlit
- **Error handling**: Agent's tool-calling handles invalid requests; system prompt sets boundaries
- **No breaking changes to UI**: Chat tab interface remains the same (messages, input, response)

## Scope

Pure LangChain agent, no LangGraph. RAG, sessions, auth unchanged.
