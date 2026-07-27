# Task 3: Create Help Desk Agent with Tool Calling

**Location:** Third task of Help Desk Agent implementation plan.
**Purpose:** Build the LangChain agent that uses the ticket tools to help users create and manage tickets.

## Requirements

Create two files:
- `src/agents/helpdesk_agent.py` - Agent implementation
- `tests/test_helpdesk_agent.py` - Agent tests

### Dependencies

This task depends on Task 2:
- Import the three tool functions from `src.tools.ticket_tools`
- Use them with LangChain's tool-calling agent

### HelpDeskAgent Class

**Constructor:**
```python
def __init__(self, user_email: str, model_name: str = "gemini-1.5-flash"):
```
- Store user_email as instance variable (used for access control)
- Initialize ChatGoogleGenerativeAI with model_name
- Set temperature=0 (deterministic)
- Create three LangChain @tool decorators wrapping the ticket_tools functions
- Create system prompt with access control guard (see below)
- Create ChatPromptTemplate with system prompt + chat history + human input + agent scratchpad
- Use create_tool_calling_agent to build the agent
- Create AgentExecutor with agent and tools

**System Prompt Pattern:**
```
You are a helpful IT Support Help Desk Agent. Your role is to:
1. Creating support tickets for IT issues
2. Checking the status of existing tickets
3. Listing all tickets for the user

IMPORTANT: You are assisting user with email: {user_email}
- Users can ONLY create tickets for themselves
- Users can ONLY check tickets they own
- All ticket operations are scoped to this user's email automatically

[Instructions for each capability...]

Always be helpful and professional.
```

**Public Method:**
```python
def run(self, user_input: str) -> str:
    """Run the agent with user input and return response text."""
    result = self.executor.invoke({"input": user_input})
    return result.get("output", "")
```

### LangChain Tool Wrapping

Each ticket tool must be wrapped with @tool decorator:
```python
@tool
def create_ticket(title: str, description: str) -> dict:
    """Create a new support ticket."""
    return create_ticket_tool(self.user_email, title, description)
```

The wrapper:
- Takes simplified parameters (user_email removed because it's scoped to the agent instance)
- Calls the underlying tool with self.user_email added
- Returns dict that the agent can parse

### Tests (2 required, minimal)

1. `test_agent_receives_user_email` - Verify agent stores user_email correctly
2. `test_agent_can_be_initialized` - Verify agent initializes without error

(More integration tests happen in Task 5. This task focuses on agent structure.)

### Global Constraints

- Use Gemini via langchain_google_genai (existing dependency)
- Use temperature=0 for deterministic responses
- LangChain version: use existing project dependencies (don't add new versions)
- System prompt must enforce user scoping (not just in tools, but in agent instruction)

### Expected Test Output

All tests pass:
```
tests/test_helpdesk_agent.py::test_agent_receives_user_email PASSED
tests/test_helpdesk_agent.py::test_agent_can_be_initialized PASSED
```

### Implementation Notes

- Use ChatPromptTemplate.from_messages() with MessagesPlaceholder for chat history
- The @tool decorator creates LangChain tools from Python functions
- AgentExecutor runs the agentic loop (think → choose tool → run tool → repeat)
- verbose=False in executor (production mode)
- Access control is enforced by the system prompt AND by the underlying tools (defense in depth)
