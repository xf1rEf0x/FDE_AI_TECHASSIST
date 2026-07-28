# tests/test_asset_support_agent.py
"""Tests for the Asset & Support Agent."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from src.agents import asset_support_agent as asa


def _mock_llm(responses):
    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    llm = MagicMock()
    llm.bind_tools.return_value = llm_with_tools
    return llm


def test_lookup_instruction_never_creates_ticket(monkeypatch):
    monkeypatch.setattr(asa, "search_employee_assets", MagicMock(invoke=MagicMock(return_value="Laptop found.")))
    monkeypatch.setattr(asa, "check_asset_warranty", MagicMock(invoke=MagicMock(return_value="ACTIVE")))
    create_ticket_mock = MagicMock()
    monkeypatch.setattr(asa, "create_ticket_tool", create_ticket_mock)

    responses = [
        AIMessage(content="", tool_calls=[{"name": "search_asset", "args": {"query": "Alice"}, "id": "1"}]),
        AIMessage(content="", tool_calls=[{"name": "check_warranty", "args": {"query": "Alice"}, "id": "2"}]),
        AIMessage(content="Found the laptop, warranty is active."),
    ]
    llm = _mock_llm(responses)

    result = asa.run_asset_support_agent(
        llm, "alice@company.com", "EMP001", False,
        instruction="Look up the asset and check warranty only, do not create a ticket.",
        context="Issue: VPN Connection, Device: Company Laptop",
    )

    assert "warranty is active" in result
    create_ticket_mock.assert_not_called()


def test_confirmed_instruction_creates_ticket(monkeypatch):
    monkeypatch.setattr(asa, "search_employee_assets", MagicMock())
    monkeypatch.setattr(asa, "check_asset_warranty", MagicMock())
    create_ticket_mock = MagicMock(
        return_value={"status": "success", "ticket_id": "tkt-1", "message": "Ticket tkt-1 created successfully."}
    )
    monkeypatch.setattr(asa, "create_ticket_tool", create_ticket_mock)

    responses = [
        AIMessage(
            content="",
            tool_calls=[{"name": "create_ticket", "args": {"title": "VPN issue", "description": "Cannot connect"}, "id": "1"}],
        ),
        AIMessage(content="Ticket tkt-1 created."),
    ]
    llm = _mock_llm(responses)

    result = asa.run_asset_support_agent(
        llm, "alice@company.com", "EMP001", False,
        instruction="The user confirmed. Create the ticket now.",
        context="Issue: VPN Connection, Device: Company Laptop",
    )

    assert "tkt-1" in result
    create_ticket_mock.assert_called_once_with("alice@company.com", "VPN issue", "Cannot connect")
