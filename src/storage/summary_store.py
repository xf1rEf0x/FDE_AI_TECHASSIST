"""Support summary storage layer (mirrors TicketStore's shape)."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel


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
        """Initialize store, creating parent directories and empty file if missing."""
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
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
        """Load summaries from JSON file."""
        if not self.store_path.exists():
            return []
        with open(self.store_path) as f:
            return json.load(f)

    def _save(self, records: list[dict]) -> None:
        """Save summaries to JSON file."""
        with open(self.store_path, "w") as f:
            json.dump(records, f, indent=2)
