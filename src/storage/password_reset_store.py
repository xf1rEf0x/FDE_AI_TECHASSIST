"""Password reset request storage layer with JSON persistence and access control."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel


class PasswordResetRequest(BaseModel):
    """Password reset request data model."""

    id: str
    user_email: str
    status: str = "pending"  # pending, resolved
    requested_at: str
    resolved_at: str | None = None


class PasswordResetStore:
    """Manages password reset request storage with per-user access control."""

    def __init__(self, store_path: str = "data/password_reset_requests.json"):
        """Initialize store, creating parent directories and empty file if missing."""
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._save([])

    def create_request(self, user_email: str) -> PasswordResetRequest:
        """Create and persist a new password reset request."""
        request = PasswordResetRequest(
            id=str(uuid.uuid4()),
            user_email=user_email,
            status="pending",
            requested_at=datetime.now(timezone.utc).isoformat(),
        )
        requests = self._load()
        requests.append(request.model_dump())
        self._save(requests)
        return request

    def list_user_requests(self, user_email: str) -> list[PasswordResetRequest]:
        """List all password reset requests raised by the user."""
        requests = self._load()
        return [
            PasswordResetRequest(**r) for r in requests if r["user_email"] == user_email
        ]

    def list_pending_requests(self) -> list[PasswordResetRequest]:
        """List all pending password reset requests (used by admins)."""
        requests = self._load()
        return [PasswordResetRequest(**r) for r in requests if r["status"] == "pending"]

    def _load(self) -> list[dict]:
        """Load requests from JSON file."""
        if not self.store_path.exists():
            return []
        with open(self.store_path) as f:
            return json.load(f)

    def _save(self, requests: list[dict]) -> None:
        """Save requests to JSON file."""
        with open(self.store_path, "w") as f:
            json.dump(requests, f, indent=2)
