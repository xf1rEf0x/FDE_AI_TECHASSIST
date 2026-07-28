"""Tests for generate_summary_tool."""

from unittest.mock import MagicMock
from src.tools.summary_tools import generate_summary_tool
from src.storage.summary_store import SupportSummary, SummaryStore


def test_generate_summary_tool(monkeypatch):
    mock_store = MagicMock(spec=SummaryStore)
    mock_store.save_summary.return_value = SupportSummary(
        id="sum-123",
        user_email="alice@company.com",
        summary="Ticket created, warranty active.",
        ticket_id="tkt-1",
        created_at="2026-07-28T10:00:00+00:00",
    )
    monkeypatch.setattr("src.tools.summary_tools.summary_store", mock_store)

    result = generate_summary_tool("alice@company.com", "Ticket created, warranty active.", "tkt-1")

    assert result["status"] == "success"
    assert result["summary_id"] == "sum-123"
    assert "sum-123" in result["message"]
    mock_store.save_summary.assert_called_once_with(
        "alice@company.com", "Ticket created, warranty active.", "tkt-1"
    )
