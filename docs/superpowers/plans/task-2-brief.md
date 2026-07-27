# Task 2: Implement Ticket Tools

**Location:** Second task of Help Desk Agent implementation plan.
**Purpose:** Create tool wrappers that agents will call to create, check, and list tickets.

## Requirements

Create two files:
- `src/tools/ticket_tools.py` - Tool implementations
- `tests/test_ticket_tools.py` - Tool tests

### Dependencies

This task depends on Task 1:
- Import `TicketStore` from `src.storage.ticket_store`
- Create a module-level `ticket_store` instance: `ticket_store = TicketStore("data/tickets.json")`

### Three Tool Functions

All tools enforce access control by scoping to `user_email`:

1. `create_ticket_tool(user_email: str, title: str, description: str) -> dict`
   - Call: `ticket_store.create_ticket(user_email, title, description)`
   - Return dict with keys: `status` ("success"), `ticket_id` (str), `message` (str)
   - Example return: `{"status": "success", "ticket_id": "abc-123", "message": "Ticket created..."`

2. `check_ticket_status_tool(user_email: str, ticket_id: str) -> dict`
   - Call: `ticket_store.get_ticket(ticket_id, user_email)`
   - If ticket found AND user owns it, return: `{"status": "success", "ticket": {...}}`
   - Ticket dict should include: `ticket_id`, `title`, `description`, `status`, `created_at`
   - If ticket not found or access denied: `{"status": "error", "message": "Ticket not found or access denied."}`

3. `list_tickets_tool(user_email: str) -> dict`
   - Call: `ticket_store.list_user_tickets(user_email)`
   - Return: `{"status": "success", "tickets": [...]}`
   - Each ticket in list: `ticket_id`, `title`, `status`, `created_at`

### Tests (4 total)

All tests use a monkeypatch fixture to temporarily replace `ticket_store` with a test instance.

1. `test_create_ticket_tool` - Create succeeds, returns ticket_id
2. `test_check_ticket_status_tool` - Owner can check their ticket
3. `test_check_ticket_status_tool_denied_other_user` - Other users get "access denied" error
4. `test_list_tickets_tool` - List returns only user's tickets

### Global Constraints

- No new external dependencies (only use TicketStore from Task 1)
- Tools are stateless (TicketStore handles state)
- Return dicts, not Pydantic models (agent will parse)
- Access control via user_email parameter (not inferred)

### Expected Test Output

All 4 tests pass:
```
tests/test_ticket_tools.py::test_create_ticket_tool PASSED
tests/test_ticket_tools.py::test_check_ticket_status_tool PASSED
tests/test_ticket_tools.py::test_check_ticket_status_tool_denied_other_user PASSED
tests/test_ticket_tools.py::test_list_tickets_tool PASSED
```

### Implementation Notes

- Tools are pure functions (no class)
- TicketStore instance is module-level (shared across all calls)
- Return format matches what LangChain agents expect (dicts, not Pydantic)
