# Task 5: End-to-End Integration Tests

**Location:** Fifth task of Help Desk Agent implementation plan.
**Purpose:** Create integration test suite covering full workflows and access control.

## Requirements

Create one file:
- `tests/test_helpdesk_integration.py` - Integration test suite

### Dependencies

This task depends on Tasks 1-3:
- Import HelpDeskAgent from src.agents.helpdesk_agent
- Import TicketStore from src.storage.ticket_store
- Use src.tools.ticket_tools for monkeypatching

### Test Fixture

Create a fixture that sets up a fresh TicketStore for testing:

```python
@pytest.fixture
def integration_setup():
    """Set up a fresh ticket store for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "tickets.json")
        original_store = src.tools.ticket_tools.ticket_store
        src.tools.ticket_tools.ticket_store = TicketStore(store_path)
        
        yield src.tools.ticket_tools.ticket_store
        
        src.tools.ticket_tools.ticket_store = original_store
```

### Three Test Cases

1. **test_create_and_check_ticket_workflow**
   - Agent creates a ticket via run("Create a ticket for my VPN is not working")
   - Verify ticket exists in storage
   - Agent checks ticket status via run(f"Check status of ticket {ticket_id}")
   - Verify response contains ticket details
   - Assert: Both operations succeed end-to-end

2. **test_access_control_enforcement**
   - Alice creates a ticket
   - Bob tries to check Alice's ticket using its ID
   - Verify Bob gets "not found" or "access" error message
   - Assert: Access control prevents unauthorized viewing

3. **test_multiple_tickets_per_user**
   - Agent creates two tickets in separate run() calls
   - Verify both tickets exist in storage for that user
   - Assert: User can create and manage multiple tickets

### Global Constraints

- Use monkeypatch/temp TicketStore (no real data/tickets.json)
- Each test is independent (fresh store)
- Tests exercise the full stack: agent → tools → storage

### Expected Test Output

All 3 tests pass:
```
tests/test_helpdesk_integration.py::test_create_and_check_ticket_workflow PASSED
tests/test_helpdesk_integration.py::test_access_control_enforcement PASSED
tests/test_helpdesk_integration.py::test_multiple_tickets_per_user PASSED
```

### Implementation Notes

- These tests are "black-box" from the agent's perspective (only call run())
- Tests verify that the agent correctly uses the tools
- Access control is tested end-to-end (user can't see other user's tickets)
