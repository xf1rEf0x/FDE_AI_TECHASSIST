# Help Desk Agent

## Overview

The Help Desk Agent is a LangChain-based AI agent that manages IT support tickets for TechAssist's 12,000-employee helpdesk. It automates three core ticket operations:

1. **Ticket Creation** — Allow users to create new support tickets for IT issues (e.g., "My VPN is down", "Need software installed")
2. **Status Checking** — Enable users to track the progress of tickets they own
3. **Ticket Listing** — Let users view all their active and historical support tickets

The agent uses the Gemini API for natural language understanding and LangGraph for agentic tool calling. Access control is enforced at the tool level: users can only view and create tickets for themselves.

## Features

### Create Tickets
Users can describe their IT issue in natural language. The agent extracts the title and description, creates a ticket with a unique UUID ID, and persists it to a JSON file (`data/tickets.json`). Each ticket is automatically scoped to the user's email address.

Example: "Create a ticket for my laptop not connecting to the VPN"

### Check Status
Users can ask about a specific ticket using its ID. The agent retrieves the ticket details and displays the title, description, status, and creation date. Access control ensures users can only check their own tickets.

Example: "What's the status of ticket 123e4567-e89b-12d3-a456-426614174000?"

### List Tickets
Users can request a summary of all their tickets (open, closed, pending, etc.). The agent displays a table or list of all tickets owned by the user, showing ticket ID, title, status, and creation date.

Example: "Show me all my tickets"

### Access Control
User email is passed from the Streamlit sidebar (in production, should come from authenticated session). All ticket operations automatically scope to the current user's email address. Ticket IDs are UUIDs (not sequential), making them difficult to guess and preventing enumeration attacks. Access control is enforced at the tool level, not just the UI.

## Architecture

### Components

#### TicketStore (`src/storage/ticket_store.py`)
Handles persistent storage of tickets in JSON format (`data/tickets.json`). Provides methods for:
- `create_ticket(owner_email, title, description)` — Create and persist a new ticket
- `get_ticket(ticket_id, owner_email)` — Retrieve a ticket with access control enforcement
- `list_user_tickets(owner_email)` — List all tickets owned by a user
- `update_ticket_status(ticket_id, owner_email, status)` — Update ticket status with access control

All methods enforce per-user access control: operations fail silently if the requesting user is not the ticket owner.

#### Ticket Tools (`src/tools/ticket_tools.py`)
Three tool functions that wrap TicketStore methods for use in agents:
- `create_ticket_tool(user_email, title, description)` — Creates a ticket and returns success status + ticket ID
- `check_ticket_status_tool(user_email, ticket_id)` — Retrieves ticket details or returns "not found" error
- `list_tickets_tool(user_email)` — Returns a list of all user's tickets

Each function includes the user_email parameter, ensuring tools are scoped to the calling user.

#### HelpDeskAgent (`src/agents/helpdesk_agent.py`)
A LangChain agent that uses the Gemini API to parse user input and invoke ticket tools. The agent:
- Wraps the three ticket tools with automatic user_email scoping
- Uses a system prompt that reinforces access control rules
- Returns natural language responses (e.g., "Your ticket 12345 has been created successfully")
- Powered by `gemini-1.5-flash` (configurable)
- Uses `create_react_agent` from LangGraph for orchestration

### Data Model

Each ticket in `data/tickets.json` has the following JSON structure:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "owner_email": "alice@techassist.com",
  "title": "VPN Connection Failing",
  "description": "Cannot connect to corporate VPN from home. Getting timeout errors.",
  "status": "open",
  "created_at": "2026-07-27T14:23:45.123456+00:00",
  "updated_at": "2026-07-27T14:23:45.123456+00:00"
}
```

**Fields:**
- `id` (str, UUID) — Unique ticket identifier, generated at creation
- `owner_email` (str) — Email of the user who created the ticket (enforced for access control)
- `title` (str) — Short summary of the issue
- `description` (str) — Detailed description provided by the user
- `status` (str, default "open") — Current ticket status (e.g., "open", "in_progress", "resolved", "closed")
- `created_at` (str, ISO 8601) — UTC timestamp when ticket was created
- `updated_at` (str, ISO 8601) — UTC timestamp of last modification

## Usage

### In Code

```python
from src.agents.helpdesk_agent import HelpDeskAgent

# Initialize the agent with a user's email
agent = HelpDeskAgent(user_email="alice@techassist.com")

# Run the agent with natural language input
response = agent.run("Create a ticket for my VPN is down")
print(response)
# Output: "Your ticket 123e4567-e89b-12d3-a456-426614174000 has been created successfully."

# Check ticket status
response = agent.run("What's the status of ticket 123e4567-e89b-12d3-a456-426614174000?")
print(response)

# List all tickets
response = agent.run("Show me all my tickets")
print(response)
```

### In Streamlit UI

The Help Desk tab in the Streamlit app (`app.py`) integrates the agent:

1. User enters their email in the sidebar (under "User Settings")
2. User navigates to the "Help Desk" tab
3. User types a natural language request in the chat box
4. Agent processes the request and returns a response
5. Chat history is maintained in Streamlit session state

Example Streamlit flow:
```
User: "Create a ticket for my laptop keeps crashing"
Agent: "I've created ticket 12345678 for you. I'll keep monitoring it."

User: "What's the status of 12345678?"
Agent: "Your ticket 12345678 (Laptop Crashes) is currently open, created on 2026-07-27."

User: "List my tickets"
Agent: "You have 3 tickets:
  - 12345678 (Laptop Crashes) - open
  - 87654321 (Software Install) - resolved
  - 11111111 (Network Issue) - in_progress"
```

## Testing

Run all ticket-related tests:

```bash
pytest tests/test_ticket_store.py tests/test_ticket_tools.py tests/test_helpdesk_agent.py tests/test_helpdesk_integration.py -v
```

Individual test files:
- `tests/test_ticket_store.py` — Tests for TicketStore creation, retrieval, listing, and access control
- `tests/test_ticket_tools.py` — Tests for the three ticket tools
- `tests/test_helpdesk_agent.py` — Tests for agent initialization and tool invocation
- `tests/test_helpdesk_integration.py` — Integration tests for end-to-end agent workflows

Run a single test file:
```bash
pytest tests/test_ticket_store.py -v
```

## Security Notes

### User Scoping
User email is passed from the Streamlit sidebar under "User Settings". In production, user identity should be sourced from an authenticated session (e.g., OAuth, SAML, or SSO) rather than user input. Never trust the email field in a real deployment without backend validation.

### UUID-Based IDs
Ticket IDs are UUIDs (e.g., `123e4567-e89b-12d3-a456-426614174000`), not sequential numbers. This prevents attackers from guessing or enumerating ticket IDs. The UUID space is large enough that random guessing is infeasible.

### Access Control at Tool Level
Access control is enforced in the TicketStore class, not just in the UI. Every `get_ticket()` and `list_user_tickets()` call checks `owner_email` against the request. If a user attempts to check another user's ticket, the tool returns `None` or "not found". This defense-in-depth approach protects against both UI bypasses and direct API abuse.

### JSON File Permissions
In a production environment, `data/tickets.json` should have restricted file permissions (e.g., readable only by the application process) and should be moved to a database. For development, the JSON file is suitable for prototyping.

### Gemini API Key
The Gemini API key is set via the `GOOGLE_API_KEY` environment variable. Ensure `.env` is not committed to version control and that keys are rotated regularly.
