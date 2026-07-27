"""Tests for ticket storage layer with access control."""

import pytest
import json
from pathlib import Path
from datetime import datetime
from src.storage.ticket_store import Ticket, TicketStore


@pytest.fixture
def temp_store(tmp_path):
    """Fixture: TicketStore with temp directory."""
    store_path = tmp_path / "tickets.json"
    return TicketStore(str(store_path))


class TestTicketModel:
    """Tests for Ticket Pydantic model."""

    def test_ticket_creation_with_all_fields(self):
        """Verify Ticket model accepts all required fields."""
        ticket = Ticket(
            id="test-id",
            owner_email="user@example.com",
            title="Test Issue",
            description="This is a test",
            status="open",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert ticket.id == "test-id"
        assert ticket.owner_email == "user@example.com"
        assert ticket.title == "Test Issue"
        assert ticket.status == "open"


class TestTicketStoreInit:
    """Tests for TicketStore initialization."""

    def test_init_creates_store_path(self, tmp_path):
        """TicketStore.__init__ creates parent directories if missing."""
        store_path = tmp_path / "subdir" / "tickets.json"
        store = TicketStore(str(store_path))
        assert store_path.parent.exists()

    def test_init_creates_empty_json_file(self, tmp_path):
        """TicketStore.__init__ creates empty JSON file if missing."""
        store_path = tmp_path / "tickets.json"
        store = TicketStore(str(store_path))
        assert store_path.exists()
        with open(store_path) as f:
            data = json.load(f)
        assert data == []


class TestCreateTicket:
    """Tests for create_ticket method."""

    def test_create_ticket(self, temp_store):
        """Create ticket and verify all fields."""
        ticket = temp_store.create_ticket(
            owner_email="alice@example.com",
            title="VPN Access Issue",
            description="Cannot connect to VPN",
        )
        assert ticket.owner_email == "alice@example.com"
        assert ticket.title == "VPN Access Issue"
        assert ticket.description == "Cannot connect to VPN"
        assert ticket.status == "open"
        assert ticket.id is not None
        assert len(ticket.id) > 0
        assert ticket.created_at is not None
        assert ticket.updated_at is not None
        # Verify ISO-8601 format
        datetime.fromisoformat(ticket.created_at)
        datetime.fromisoformat(ticket.updated_at)

    def test_create_ticket_persistence(self, temp_store):
        """Created ticket is persisted to JSON."""
        ticket = temp_store.create_ticket(
            owner_email="bob@example.com",
            title="Test",
            description="Test description",
        )
        # Manually reload from disk
        with open(temp_store.store_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["id"] == ticket.id
        assert data[0]["owner_email"] == "bob@example.com"


class TestGetTicket:
    """Tests for get_ticket method."""

    def test_get_ticket_by_owner(self, temp_store):
        """Owner can retrieve their ticket."""
        ticket = temp_store.create_ticket(
            owner_email="alice@example.com",
            title="Issue 1",
            description="Description 1",
        )
        retrieved = temp_store.get_ticket(ticket.id, "alice@example.com")
        assert retrieved is not None
        assert retrieved.id == ticket.id
        assert retrieved.owner_email == "alice@example.com"

    def test_get_ticket_denies_other_user(self, temp_store):
        """Other users cannot access ticket (access control enforced)."""
        ticket = temp_store.create_ticket(
            owner_email="alice@example.com",
            title="Issue 1",
            description="Description 1",
        )
        # Bob tries to access Alice's ticket
        retrieved = temp_store.get_ticket(ticket.id, "bob@example.com")
        assert retrieved is None

    def test_get_ticket_not_found(self, temp_store):
        """get_ticket returns None for non-existent ticket."""
        retrieved = temp_store.get_ticket("nonexistent-id", "alice@example.com")
        assert retrieved is None


class TestListUserTickets:
    """Tests for list_user_tickets method."""

    def test_list_user_tickets(self, temp_store):
        """List returns only user's tickets."""
        # Create tickets for two users
        t1 = temp_store.create_ticket(
            owner_email="alice@example.com", title="Alice Issue 1", description="A1"
        )
        t2 = temp_store.create_ticket(
            owner_email="alice@example.com", title="Alice Issue 2", description="A2"
        )
        t3 = temp_store.create_ticket(
            owner_email="bob@example.com", title="Bob Issue 1", description="B1"
        )
        # Alice should see only her tickets
        alice_tickets = temp_store.list_user_tickets("alice@example.com")
        assert len(alice_tickets) == 2
        assert all(t.owner_email == "alice@example.com" for t in alice_tickets)
        assert t1.id in [t.id for t in alice_tickets]
        assert t2.id in [t.id for t in alice_tickets]

    def test_list_user_tickets_empty(self, temp_store):
        """List returns empty list if user has no tickets."""
        tickets = temp_store.list_user_tickets("charlie@example.com")
        assert tickets == []

    def test_list_user_tickets_no_cross_access(self, temp_store):
        """User's list doesn't include other users' tickets."""
        temp_store.create_ticket(
            owner_email="alice@example.com", title="Alice Issue", description="A"
        )
        temp_store.create_ticket(
            owner_email="bob@example.com", title="Bob Issue", description="B"
        )
        bob_tickets = temp_store.list_user_tickets("bob@example.com")
        assert len(bob_tickets) == 1
        assert bob_tickets[0].owner_email == "bob@example.com"


class TestUpdateTicketStatus:
    """Tests for update_ticket_status method."""

    def test_update_ticket_status(self, temp_store):
        """Owner can update status."""
        ticket = temp_store.create_ticket(
            owner_email="alice@example.com", title="Issue", description="Desc"
        )
        original_updated_at = ticket.updated_at
        updated = temp_store.update_ticket_status(
            ticket.id, "alice@example.com", "resolved"
        )
        assert updated is not None
        assert updated.status == "resolved"
        # updated_at should be newer
        assert updated.updated_at >= original_updated_at

    def test_update_ticket_status_denies_other_user(self, temp_store):
        """Other users cannot update ticket (access control enforced)."""
        ticket = temp_store.create_ticket(
            owner_email="alice@example.com", title="Issue", description="Desc"
        )
        # Bob tries to update Alice's ticket
        updated = temp_store.update_ticket_status(
            ticket.id, "bob@example.com", "resolved"
        )
        assert updated is None
        # Verify ticket is still open
        retrieved = temp_store.get_ticket(ticket.id, "alice@example.com")
        assert retrieved.status == "open"

    def test_update_ticket_not_found(self, temp_store):
        """update_ticket_status returns None if ticket doesn't exist."""
        updated = temp_store.update_ticket_status(
            "nonexistent", "alice@example.com", "resolved"
        )
        assert updated is None


class TestPersistence:
    """Tests for persistence across store instances."""

    def test_persistence(self, tmp_path):
        """Tickets survive reload from disk."""
        store_path = tmp_path / "tickets.json"
        # Create ticket with first store instance
        store1 = TicketStore(str(store_path))
        ticket = store1.create_ticket(
            owner_email="alice@example.com", title="Issue", description="Desc"
        )
        ticket_id = ticket.id
        # Create new store instance and verify ticket persists
        store2 = TicketStore(str(store_path))
        retrieved = store2.get_ticket(ticket_id, "alice@example.com")
        assert retrieved is not None
        assert retrieved.id == ticket_id
        assert retrieved.owner_email == "alice@example.com"
