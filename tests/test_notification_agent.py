"""Tests for the Notification Agent."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from src.agents import notification_agent as na


def _mock_llm(responses):
    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    llm = MagicMock()
    llm.bind_tools.return_value = llm_with_tools
    return llm


def test_preview_instruction_does_not_save_summary(monkeypatch):
    generate_summary_mock = MagicMock()
    monkeypatch.setattr(na, "generate_summary_tool", generate_summary_mock)

    llm = _mock_llm([AIMessage(content="### Ticket Preview\nConfirm?")])

    result = na.run_notification_agent(
        llm, "alice@company.com",
        instruction="Preview the ticket details and ask for confirmation.",
        context="Issue: VPN Connection, Device: Company Laptop, Warranty: ACTIVE",
    )

    assert "Confirm?" in result
    generate_summary_mock.assert_not_called()


def test_confirmed_instruction_saves_summary(monkeypatch):
    generate_summary_mock = MagicMock(
        return_value={"status": "success", "summary_id": "sum-1", "message": "Summary sum-1 saved."}
    )
    monkeypatch.setattr(na, "generate_summary_tool", generate_summary_mock)

    responses = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": "generate_summary",
                "args": {"summary": "Ticket tkt-1 created for VPN issue.", "ticket_id": "tkt-1"},
                "id": "1",
            }],
        ),
        AIMessage(content="All done, summary saved."),
    ]
    llm = _mock_llm(responses)

    result = na.run_notification_agent(
        llm, "alice@company.com",
        instruction="The user confirmed and the ticket is created. Generate the summary.",
        context="Ticket ID: tkt-1",
    )

    assert "summary saved" in result
    generate_summary_mock.assert_called_once_with(
        "alice@company.com", "Ticket tkt-1 created for VPN issue.", "tkt-1"
    )
