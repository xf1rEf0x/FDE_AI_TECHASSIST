"""Software request storage layer with JSON persistence and access control."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel

from src.storage.blob_store import load_blob, save_blob, is_remote


class SoftwareRequest(BaseModel):
    """Software request data model."""

    id: str
    requester_email: str
    software_name: str
    version: str
    justification: str
    status: str = "pending"  # pending, approved, rejected
    request_date: str
    approved_by: str | None = None  # Name of approver
    approved_date: str | None = None
    rejection_reason: str | None = None


class SoftwareRequestStore:
    """Manages software request storage with per-user access control."""

    def __init__(self, store_path: str = "data/software_requests.json"):
        """Initialize store, eagerly creating the local file if not using Redis."""
        self.store_path = store_path
        if not is_remote() and not Path(store_path).exists():
            self._save([])

    def create_request(
        self, requester_email: str, software_name: str, version: str, justification: str
    ) -> SoftwareRequest:
        """Create and persist a new software request."""
        request = SoftwareRequest(
            id=str(uuid.uuid4()),
            requester_email=requester_email,
            software_name=software_name,
            version=version,
            justification=justification,
            status="pending",
            request_date=datetime.now(timezone.utc).isoformat(),
        )
        requests = self._load()
        requests.append(request.model_dump())
        self._save(requests)
        return request

    def get_request(self, request_id: str, requester_email: str) -> SoftwareRequest | None:
        """Get request if requester_email matches (access control enforced)."""
        requests = self._load()
        for req_data in requests:
            if req_data["id"] == request_id:
                # Access control: only return if requester matches
                if req_data["requester_email"] == requester_email:
                    return SoftwareRequest(**req_data)
                else:
                    return None
        return None

    def list_user_requests(self, requester_email: str) -> list[SoftwareRequest]:
        """List all requests created by the user."""
        requests = self._load()
        user_requests = [
            SoftwareRequest(**r) for r in requests if r["requester_email"] == requester_email
        ]
        return user_requests

    def approve_request(
        self, request_id: str, approver_email: str, approved_by_name: str
    ) -> SoftwareRequest | None:
        """Approve a pending request (admin/approver only)."""
        requests = self._load()
        for i, req_data in enumerate(requests):
            if req_data["id"] == request_id:
                if req_data["status"] != "pending":
                    return None  # Can only approve pending requests
                req_data["status"] = "approved"
                req_data["approved_by"] = approved_by_name
                req_data["approved_date"] = datetime.now(timezone.utc).isoformat()
                self._save(requests)
                return SoftwareRequest(**req_data)
        return None

    def reject_request(
        self, request_id: str, approver_email: str, reason: str
    ) -> SoftwareRequest | None:
        """Reject a pending request (admin/approver only)."""
        requests = self._load()
        for i, req_data in enumerate(requests):
            if req_data["id"] == request_id:
                if req_data["status"] != "pending":
                    return None  # Can only reject pending requests
                req_data["status"] = "rejected"
                req_data["rejection_reason"] = reason
                self._save(requests)
                return SoftwareRequest(**req_data)
        return None

    def list_pending_requests(self) -> list[SoftwareRequest]:
        """List all pending requests (used by admins)."""
        requests = self._load()
        pending = [
            SoftwareRequest(**r) for r in requests if r["status"] == "pending"
        ]
        return pending

    def _load(self) -> list[dict]:
        """Load requests."""
        return load_blob("software_requests", self.store_path, [])

    def _save(self, requests: list[dict]) -> None:
        """Save requests."""
        save_blob("software_requests", self.store_path, requests)
