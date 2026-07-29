"""Support summary storage layer (mirrors TicketStore's shape)."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel

from src.storage.blob_store import load_blob, save_blob, is_remote


class SupportSummary(BaseModel):
    """A saved summary of a support interaction."""

    id: str
    user_email: str
    summary: str
    ticket_id: str | None = None
    created_at: str


class SummaryStore:
    """Manages support summary storage."""

    def __init__(self, store_path: str = "data/support_summaries.json"):
        """Initialize store, eagerly creating the local file if not using Redis."""
        self.store_path = store_path
        if not is_remote() and not Path(store_path).exists():
            self._save([])

    def save_summary(
        self, user_email: str, summary: str, ticket_id: str | None = None
    ) -> SupportSummary:
        """Create and persist a new summary record."""
        record = SupportSummary(
            id=str(uuid.uuid4()),
            user_email=user_email,
            summary=summary,
            ticket_id=ticket_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        records = self._load()
        records.append(record.model_dump())
        self._save(records)
        return record

    def list_summaries(self, user_email: str) -> list[SupportSummary]:
        """List all summaries for the user."""
        records = self._load()
        return [SupportSummary(**r) for r in records if r["user_email"] == user_email]

    def _load(self) -> list[dict]:
        """Load summaries."""
        return load_blob("support_summaries", self.store_path, [])

    def _save(self, records: list[dict]) -> None:
        """Save summaries."""
        save_blob("support_summaries", self.store_path, records)
