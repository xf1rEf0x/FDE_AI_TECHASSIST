"""Tests for ticket tools (create, check, list)."""

import pytest
from unittest.mock import patch, MagicMock
from src.tools.ticket_tools import (
    create_ticket_tool,
    check_ticket_status_tool,
    list_tickets_tool,
)
from src.storage.ticket_store import Ticket, TicketStore


@pytest.fixture
def mock_ticket_store(monkeypatch):
    """Fixture: mock TicketStore instance for testing."""
    mock_store = MagicMock(spec=TicketStore)

    # Mock create_ticket to return a Ticket
    def mock_create(owner_email, title, description):
        return Ticket(
            id="ticket-123",
            owner_email=owner_email,
            title=title,
            description=description,
            status="open",
            created_at="2026-07-27T10:00:00+00:00",
            updated_at="2026-07-27T10:00:00+00:00",
        )

    mock_store.create_ticket = mock_create

    # Mock get_ticket to return a Ticket or None
    def mock_get(ticket_id, owner_email):
        if ticket_id == "ticket-123" and owner_email == "alice@company.com":
            return Ticket(
                id="ticket-123",
                owner_email="alice@company.com",
                title="Cannot login",
                description="My account is locked",
                status="open",
                created_at="2026-07-27T10:00:00+00:00",
                updated_at="2026-07-27T10:00:00+00:00",
            )
        return None

    mock_store.get_ticket = mock_get

    # Mock list_user_tickets to return a list of Tickets
    def mock_list(owner_email):
        if owner_email == "alice@company.com":
            return [
                Ticket(
                    id="ticket-123",
                    owner_email="alice@company.com",
                    title="Cannot login",
                    description="My account is locked",
                    status="open",
                    created_at="2026-07-27T10:00:00+00:00",
                    updated_at="2026-07-27T10:00:00+00:00",
                ),
                Ticket(
                    id="ticket-456",
                    owner_email="alice@company.com",
                    title="Software request",
                    description="Need Python IDE",
                    status="resolved",
                    created_at="2026-07-26T10:00:00+00:00",
                    updated_at="2026-07-27T14:30:00+00:00",
                ),
            ]
        elif owner_email == "bob@company.com":
            return [
                Ticket(
                    id="ticket-789",
                    owner_email="bob@company.com",
                    title="VPN access",
                    description="Cannot connect to VPN",
                    status="open",
                    created_at="2026-07-27T09:00:00+00:00",
                    updated_at="2026-07-27T09:00:00+00:00",
                )
            ]
        return []

    mock_store.list_user_tickets = mock_list

    # Patch the module-level ticket_store
    monkeypatch.setattr("src.tools.ticket_tools.ticket_store", mock_store)

    return mock_store


class TestCreateTicketTool:
    """Tests for create_ticket_tool."""

    def test_create_ticket_tool(self, mock_ticket_store):
        """Test: Create ticket succeeds and returns ticket_id."""
        result = create_ticket_tool(
            user_email="alice@company.com",
            title="Cannot login",
            description="My account is locked",
        )

        assert result["status"] == "success"
        assert result["ticket_id"] == "ticket-123"
        assert "message" in result
        assert "created" in result["message"].lower() or "success" in result["message"].lower()


class TestCheckTicketStatusTool:
    """Tests for check_ticket_status_tool."""

    def test_check_ticket_status_tool(self, mock_ticket_store):
        """Test: Owner can check their ticket."""
        result = check_ticket_status_tool(
            user_email="alice@company.com",
            ticket_id="ticket-123",
        )

        assert result["status"] == "success"
        assert "ticket" in result
        ticket = result["ticket"]
        assert ticket["ticket_id"] == "ticket-123"
        assert ticket["title"] == "Cannot login"
        assert ticket["description"] == "My account is locked"
        assert ticket["status"] == "open"
        assert "created_at" in ticket

    def test_check_ticket_status_tool_denied_other_user(self, mock_ticket_store):
        """Test: Other users get 'access denied' error."""
        result = check_ticket_status_tool(
            user_email="bob@company.com",
            ticket_id="ticket-123",  # Alice's ticket
        )

        assert result["status"] == "error"
        assert "message" in result
        assert "not found" in result["message"].lower() or "access" in result["message"].lower()


class TestListTicketsTool:
    """Tests for list_tickets_tool."""

    def test_list_tickets_tool(self, mock_ticket_store):
        """Test: List returns only user's tickets."""
        result = list_tickets_tool(user_email="alice@company.com")

        assert result["status"] == "success"
        assert "tickets" in result
        tickets = result["tickets"]
        assert len(tickets) == 2

        # Check first ticket
        assert tickets[0]["ticket_id"] == "ticket-123"
        assert tickets[0]["title"] == "Cannot login"
        assert tickets[0]["status"] == "open"
        assert "created_at" in tickets[0]

        # Check second ticket
        assert tickets[1]["ticket_id"] == "ticket-456"
        assert tickets[1]["title"] == "Software request"
        assert tickets[1]["status"] == "resolved"
