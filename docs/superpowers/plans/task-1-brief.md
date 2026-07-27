# Task 1: Implement Ticket Storage Layer

**Location:** First task of Help Desk Agent implementation plan.
**Purpose:** Create the foundational storage layer for tickets with JSON persistence and per-user access control.

## Requirements

Create two files:
- `src/storage/ticket_store.py` - Core storage implementation
- `tests/test_ticket_store.py` - Test suite

### Data Model

Ticket model (Pydantic BaseModel):
```
id: str (UUID)
owner_email: str
title: str
description: str
status: str (default: "open")
created_at: str (ISO-8601 timestamp)
updated_at: str (ISO-8601 timestamp)
```

### TicketStore Class Methods

1. `__init__(store_path: str = "data/tickets.json")`
   - Create parent directories if missing
   - Auto-initialize empty JSON file if missing

2. `create_ticket(owner_email: str, title: str, description: str) -> Ticket`
   - Generate UUID for ticket ID
   - Set status to "open"
   - Timestamp: created_at and updated_at to current UTC time
   - Save to JSON and return Ticket object

3. `get_ticket(ticket_id: str, owner_email: str) -> Ticket | None`
   - Return ticket ONLY if owner_email matches
   - Return None if ticket not found OR user doesn't own it
   - **This enforces access control**

4. `list_user_tickets(owner_email: str) -> list[Ticket]`
   - Return all tickets where owner_email matches
   - Return empty list if user has no tickets

5. `update_ticket_status(ticket_id: str, owner_email: str, status: str) -> Ticket | None`
   - Update status only if owner_email matches
   - Update updated_at timestamp
   - Return updated Ticket or None if access denied

### Tests (7 total)

All tests use a temporary directory fixture to avoid touching real data/tickets.json.

1. `test_create_ticket` - Create ticket and verify all fields
2. `test_get_ticket_by_owner` - Owner can retrieve their ticket
3. `test_get_ticket_denies_other_user` - Other users cannot access ticket
4. `test_list_user_tickets` - List returns only user's tickets
5. `test_update_ticket_status` - Owner can update status
6. `test_update_ticket_status_denies_other_user` - Other users cannot update
7. `test_persistence` - Tickets survive reload from disk

### Global Constraints

- Use Pydantic for Ticket model validation
- JSON persistence (no database)
- Access control enforced on every operation (not just at UI level)
- UTC timestamps, ISO-8601 format
- No new external dependencies (Python stdlib + existing Pydantic)

### Expected Test Output

All 7 tests pass:
```
tests/test_ticket_store.py::test_create_ticket PASSED
tests/test_ticket_store.py::test_get_ticket_by_owner PASSED
tests/test_ticket_store.py::test_get_ticket_denies_other_user PASSED
tests/test_ticket_store.py::test_list_user_tickets PASSED
tests/test_ticket_store.py::test_update_ticket_status PASSED
tests/test_ticket_store.py::test_update_ticket_status_denies_other_user PASSED
tests/test_ticket_store.py::test_persistence PASSED
```

### Implementation Notes

- Internal methods `_load()` and `_save()` handle JSON I/O
- Path handling uses `pathlib.Path`
- Timestamp generation uses `datetime.utcnow().isoformat()`
- UUID generation uses `uuid.uuid4()`
