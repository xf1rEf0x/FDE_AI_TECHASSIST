"""Tests for password reset request tool."""

import pytest
from src.tools.password_tools import reset_password_tool, list_pending_password_reset_requests_tool
from src.storage.password_reset_store import PasswordResetRequest, PasswordResetStore


@pytest.fixture
def mock_password_reset_store(monkeypatch):
    """Fixture: mock PasswordResetStore instance for testing."""
    from unittest.mock import MagicMock

    mock_store = MagicMock(spec=PasswordResetStore)

    def mock_create(user_email):
        return PasswordResetRequest(
            id="reset-123",
            user_email=user_email,
            status="pending",
            requested_at="2026-07-27T10:00:00+00:00",
        )

    mock_store.create_request = mock_create
    monkeypatch.setattr("src.tools.password_tools.password_reset_store", mock_store)
    return mock_store


def test_reset_password_tool_returns_valid_response(mock_password_reset_store):
    """Test that reset_password_tool returns expected response structure."""
    result = reset_password_tool("alice@techassist.com")

    assert result["status"] == "success"
    assert result["request_id"] == "reset-123"
    assert "message" in result


def test_reset_password_tool_does_not_change_password(mock_password_reset_store):
    """Test that reset_password_tool no longer mutates the user's actual password."""
    from src.auth_config import USERS

    test_email = "bob@techassist.com"
    old_password = USERS[test_email]["password"]

    reset_password_tool(test_email)

    assert USERS[test_email]["password"] == old_password


def test_reset_password_tool_fails_for_nonexistent_user(mock_password_reset_store):
    """Test that raising a request for a nonexistent user returns error."""
    result = reset_password_tool("nonexistent@techassist.com")

    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_password_reset_store_persists_request(tmp_path):
    """Test that PasswordResetStore creates and saves a request."""
    store = PasswordResetStore(str(tmp_path / "password_reset_requests.json"))
    request = store.create_request("carol@techassist.com")

    assert request.status == "pending"
    requests = store.list_user_requests("carol@techassist.com")
    assert len(requests) == 1
    assert requests[0].id == request.id


def test_password_reset_store_lists_pending_requests(tmp_path):
    """Test that PasswordResetStore.list_pending_requests returns all pending requests."""
    store = PasswordResetStore(str(tmp_path / "password_reset_requests.json"))
    store.create_request("alice@techassist.com")
    store.create_request("bob@techassist.com")

    pending = store.list_pending_requests()
    assert len(pending) == 2
    assert {r.user_email for r in pending} == {"alice@techassist.com", "bob@techassist.com"}


def test_list_pending_password_reset_requests_tool(monkeypatch):
    """Test that the admin tool returns formatted pending requests."""
    from unittest.mock import MagicMock

    mock_store = MagicMock(spec=PasswordResetStore)
    mock_store.list_pending_requests.return_value = [
        PasswordResetRequest(
            id="reset-123",
            user_email="alice@techassist.com",
            status="pending",
            requested_at="2026-07-27T10:00:00+00:00",
        )
    ]
    monkeypatch.setattr("src.tools.password_tools.password_reset_store", mock_store)

    result = list_pending_password_reset_requests_tool()

    assert result["status"] == "success"
    assert len(result["requests"]) == 1
    assert result["requests"][0]["request_id"] == "reset-123"
    assert result["requests"][0]["user_email"] == "alice@techassist.com"
