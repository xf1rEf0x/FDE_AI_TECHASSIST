"""Ticket storage layer with JSON persistence and access control."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel

from src.storage.blob_store import load_blob, save_blob, is_remote


class Ticket(BaseModel):
    """Ticket data model."""

    id: str
    owner_email: str
    title: str
    description: str
    status: str = "open"
    created_at: str
    updated_at: str


class TicketStore:
    """Manages ticket storage with per-user access control."""

    def __init__(self, store_path: str = "data/tickets.json"):
        """Initialize store, eagerly creating the local file if not using Redis."""
        self.store_path = store_path
        if not is_remote() and not Path(store_path).exists():
            self._save([])

    def create_ticket(
        self, owner_email: str, title: str, description: str
    ) -> Ticket:
        """Create and persist a new ticket."""
        ticket = Ticket(
            id=str(uuid.uuid4()),
            owner_email=owner_email,
            title=title,
            description=description,
            status="open",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        tickets = self._load()
        tickets.append(ticket.model_dump())
        self._save(tickets)
        return ticket

    def get_ticket(self, ticket_id: str, owner_email: str) -> Ticket | None:
        """Get ticket if owner_email matches (access control enforced)."""
        tickets = self._load()
        for ticket_data in tickets:
            if ticket_data["id"] == ticket_id:
                # Access control: only return if owner matches
                if ticket_data["owner_email"] == owner_email:
                    return Ticket(**ticket_data)
                else:
                    return None
        return None

    def list_user_tickets(self, owner_email: str) -> list[Ticket]:
        """List all tickets owned by the user."""
        tickets = self._load()
        user_tickets = [
            Ticket(**t) for t in tickets if t["owner_email"] == owner_email
        ]
        return user_tickets

    def update_ticket_status(
        self, ticket_id: str, owner_email: str, status: str
    ) -> Ticket | None:
        """Update ticket status if owner_email matches (access control enforced)."""
        tickets = self._load()
        for i, ticket_data in enumerate(tickets):
            if ticket_data["id"] == ticket_id:
                # Access control: only update if owner matches
                if ticket_data["owner_email"] != owner_email:
                    return None
                ticket_data["status"] = status
                ticket_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save(tickets)
                return Ticket(**ticket_data)
        return None

    def _load(self) -> list[dict]:
        """Load tickets."""
        return load_blob("tickets", self.store_path, [])

    def _save(self, tickets: list[dict]) -> None:
        """Save tickets."""
        save_blob("tickets", self.store_path, tickets)
