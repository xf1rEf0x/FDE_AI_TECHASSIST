# tests/test_supervisor_agent.py
"""Integration test for SupervisorAgent's confirm-before-ticket-creation flow."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

from src.agents import asset_support_agent as asa
from src.agents import notification_agent as na
from src.agents.request_analysis_agent import RequestAnalysis
from src.agents.supervisor_agent import SupervisorAgent


def _tool_call_message(name, args, call_id):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def test_ticket_is_only_created_after_explicit_confirmation(monkeypatch):
    create_ticket_mock = MagicMock(
        return_value={"status": "success", "ticket_id": "tkt-1", "message": "Ticket tkt-1 created successfully."}
    )
    generate_summary_mock = MagicMock(
        return_value={"status": "success", "summary_id": "sum-1", "message": "Summary sum-1 saved."}
    )
    monkeypatch.setattr(asa, "create_ticket_tool", create_ticket_mock)
    monkeypatch.setattr(na, "generate_summary_tool", generate_summary_mock)

    responses = [
        # --- Turn 1: analyze, look up asset + warranty, preview, wait ---
        _tool_call_message("analyze_support_request", {"user_message": "VPN issue"}, "t1"),
        _tool_call_message(
            "asset_and_ticket_support",
            {
                "instruction": "Look up the asset and check warranty. Do not create a ticket yet.",
                "context": "Issue: VPN Connection, Device: Company Laptop",
            },
            "t2",
        ),
        _tool_call_message("search_asset", {"query": "Alice Johnson"}, "a1"),
        _tool_call_message("check_warranty", {"query": "Alice Johnson"}, "a2"),
        AIMessage(content="Found MacBook Pro, warranty is active."),
        _tool_call_message(
            "notify_user",
            {
                "instruction": "Preview the ticket details and ask for confirmation.",
                "context": "Issue: VPN Connection, Device: Company Laptop, Warranty: ACTIVE",
            },
            "t3",
        ),
        AIMessage(content="### Ticket Preview\nShall I proceed? (yes/no)"),
        AIMessage(content="### Ticket Preview\nShall I proceed? (yes/no)"),
        # --- Turn 2: user confirmed, create ticket, summarize ---
        _tool_call_message(
            "asset_and_ticket_support",
            {
                "instruction": "The user confirmed. Create the ticket now.",
                "context": "Issue: VPN Connection, Device: Company Laptop",
            },
            "t4",
        ),
        _tool_call_message(
            "create_ticket",
            {"title": "VPN Connection Issue", "description": "Company laptop cannot connect to VPN"},
            "c1",
        ),
        AIMessage(content="Ticket tkt-1 created."),
        _tool_call_message(
            "notify_user",
            {
                "instruction": "The user confirmed and the ticket is created. Generate the summary.",
                "context": "Ticket ID: tkt-1",
            },
            "t5",
        ),
        _tool_call_message(
            "generate_summary",
            {
                "summary": "Created ticket tkt-1 for a VPN connection issue on the company laptop.",
                "ticket_id": "tkt-1",
            },
            "g1",
        ),
        AIMessage(content="All done! Summary saved."),
        AIMessage(content="Ticket tkt-1 created and summary saved. Thanks!"),
    ]

    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = llm_with_tools
    mock_llm.with_structured_output.return_value.invoke.return_value = RequestAnalysis(
        issue="VPN Connection", device="Company Laptop", action="Create Ticket"
    )

    monkeypatch.setattr(
        SupervisorAgent,
        "_build_llm",
        lambda self, provider, model_name, temperature: (mock_llm, "gemini-3.5-flash-lite"),
    )

    supervisor = SupervisorAgent("alice.johnson@techassist.com", "employee", employee_id="EMP001")

    turn1_reply = supervisor.invoke(
        "My laptop isn't connecting to the company VPN. Create a ticket and check if my warranty is active."
    )
    assert "proceed" in turn1_reply.lower()
    create_ticket_mock.assert_not_called()

    turn2_reply = supervisor.invoke("Yes, go ahead.")
    assert "tkt-1" in turn2_reply
    create_ticket_mock.assert_called_once_with(
        "alice.johnson@techassist.com", "VPN Connection Issue", "Company laptop cannot connect to VPN"
    )
    generate_summary_mock.assert_called_once_with(
        "alice.johnson@techassist.com",
        "Created ticket tkt-1 for a VPN connection issue on the company laptop.",
        "tkt-1",
    )


def test_on_progress_reports_delegated_agents_in_order(monkeypatch):
    responses = [
        _tool_call_message("analyze_support_request", {"user_message": "VPN issue"}, "t1"),
        AIMessage(content="Here's what I found."),
    ]

    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = llm_with_tools
    mock_llm.with_structured_output.return_value.invoke.return_value = RequestAnalysis(
        issue="VPN Connection", device="Company Laptop", action="Diagnose"
    )

    monkeypatch.setattr(
        SupervisorAgent,
        "_build_llm",
        lambda self, provider, model_name, temperature: (mock_llm, "gemini-3.5-flash-lite"),
    )

    supervisor = SupervisorAgent("alice.johnson@techassist.com", "employee", employee_id="EMP001")

    progress_labels = []
    supervisor.invoke("My VPN is broken", on_progress=progress_labels.append)

    assert progress_labels == ["Supervisor Agent", "Request Analysis Agent", "Supervisor Agent"]
    assert supervisor.last_agents_used == ["Supervisor Agent", "Request Analysis Agent"]
