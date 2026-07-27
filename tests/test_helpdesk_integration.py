"""Integration tests for HelpDeskAgent with full stack: agent -> tools -> storage."""

import pytest
import tempfile
import os
import json
import re
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.helpdesk_agent import HelpDeskAgent
from src.storage.ticket_store import TicketStore
import src.tools.ticket_tools


@pytest.fixture
def integration_setup():
    """Set up a fresh TicketStore for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "tickets.json")
        original_store = src.tools.ticket_tools.ticket_store
        src.tools.ticket_tools.ticket_store = TicketStore(store_path)

        yield src.tools.ticket_tools.ticket_store

        src.tools.ticket_tools.ticket_store = original_store


@pytest.fixture
def mock_gemini_model():
    """Mock ChatGoogleGenerativeAI to avoid API key requirement.

    This fixture allows the agent's run() method to work without authentication
    while still exercising the full tool-calling and storage logic.
    """
    with patch("src.agents.helpdesk_agent.ChatGoogleGenerativeAI") as mock_model_class:
        mock_instance = MagicMock()
        mock_model_class.return_value = mock_instance
        yield mock_instance


def mock_react_agent_invoke(tools_dict):
    """Factory to create a mock react agent that actually calls tools.

    The mock agent will:
    1. Parse the user input to determine which tool to call
    2. Call the appropriate tool from tools_dict
    3. Return a response message with the tool result

    This allows integration testing of the full tool-calling flow.
    """
    def invoke(input_dict):
        messages = input_dict.get("messages", [])
        if not messages:
            return {"messages": [("assistant", "No input provided.")]}

        # Get the last user message
        user_msg = None
        for msg in messages:
            if isinstance(msg, tuple):
                if msg[0] == "user":
                    user_msg = msg[1]
            elif isinstance(msg, HumanMessage):
                user_msg = msg.content

        if not user_msg:
            return {"messages": [("assistant", "No user message found.")]}

        user_input_lower = user_msg.lower()

        # Simulate tool calling based on user input
        response = None

        if "create" in user_input_lower and "ticket" in user_input_lower:
            # Call create_ticket tool
            # Extract title and description from user input
            if "vpn" in user_input_lower:
                title = "VPN Access Issue"
                description = "VPN is not working"
            elif "password" in user_input_lower:
                title = "Password Reset"
                description = "Need to reset my password"
            else:
                title = "Support Request"
                description = user_msg

            # Find and call the create_ticket tool
            for tool in tools_dict:
                if tool.name == "create_ticket":
                    result = tool.func(title=title, description=description)
                    response = f"Ticket created successfully. Ticket ID: {result['ticket_id']}"
                    break

        elif "check" in user_input_lower and "ticket" in user_input_lower:
            # Extract ticket ID from user input (e.g., "Check status of ticket <id>")
            import re
            match = re.search(r"ticket\s+([a-f0-9\-]+)", user_input_lower)
            if match:
                ticket_id = match.group(1)
                # Find and call the check_ticket_status tool
                for tool in tools_dict:
                    if tool.name == "check_ticket_status":
                        result = tool.func(ticket_id=ticket_id)
                        if result["status"] == "success":
                            ticket = result["ticket"]
                            response = (
                                f"Ticket {ticket['ticket_id']}: {ticket['title']}\n"
                                f"Status: {ticket['status']}\n"
                                f"Description: {ticket['description']}"
                            )
                        else:
                            response = result["message"]
                        break
            else:
                response = "Could not parse ticket ID from request."

        elif "list" in user_input_lower and "ticket" in user_input_lower:
            # Find and call the list_tickets tool
            for tool in tools_dict:
                if tool.name == "list_tickets":
                    result = tool.func()
                    if result["tickets"]:
                        tickets_str = "\n".join(
                            f"- {t['ticket_id']}: {t['title']} ({t['status']})"
                            for t in result["tickets"]
                        )
                        response = f"Your tickets:\n{tickets_str}"
                    else:
                        response = "You have no tickets."
                    break

        if response is None:
            response = "I'm not sure how to help with that."

        return {"messages": messages + [("assistant", response)]}

    return invoke


@pytest.fixture
def mock_create_react_agent():
    """Mock create_react_agent to integrate with our tool calling simulation."""
    with patch("src.agents.helpdesk_agent.create_react_agent") as mock_agent_factory:
        def setup_agent(llm, tools, prompt=None, state_modifier=None, system_prompt=None, **kwargs):
            mock_executor = MagicMock()
            mock_executor.invoke = mock_react_agent_invoke(tools)
            return mock_executor

        mock_agent_factory.side_effect = setup_agent
        yield mock_agent_factory


class TestCreateAndCheckTicketWorkflow:
    """Test: Agent creates a ticket and checks its status end-to-end."""

    def test_create_and_check_ticket_workflow(
        self, integration_setup, mock_gemini_model, mock_create_react_agent
    ):
        """
        Test workflow:
        1. Agent creates a ticket via run("Create a ticket for my VPN is not working")
        2. Verify ticket exists in storage
        3. Agent checks ticket status via run(f"Check status of ticket {ticket_id}")
        4. Verify response contains ticket details
        """
        # Create agent for alice
        alice = HelpDeskAgent(user_email="alice@company.com")

        # Step 1: Create a ticket
        create_response = alice.run("Create a ticket for my VPN is not working")

        # Parse the response to extract ticket ID
        # Expected response format: "Ticket created successfully. Ticket ID: <id>"
        ticket_id_match = re.search(r"Ticket ID: ([a-f0-9\-]+)", create_response)
        assert ticket_id_match, f"Could not extract ticket ID from response: {create_response}"
        ticket_id = ticket_id_match.group(1)

        # Verify ticket was created in storage
        ticket = integration_setup.get_ticket(ticket_id, "alice@company.com")
        assert ticket is not None, "Ticket not found in storage after creation"
        assert ticket.title == "VPN Access Issue"
        assert ticket.owner_email == "alice@company.com"
        assert ticket.status == "open"

        # Step 2: Check ticket status
        check_response = alice.run(f"Check status of ticket {ticket_id}")

        # Verify the response contains ticket details
        assert ticket_id in check_response, "Response doesn't contain ticket ID"
        assert "VPN Access Issue" in check_response, "Response doesn't contain ticket title"
        assert "open" in check_response.lower(), "Response doesn't contain ticket status"


class TestAccessControlEnforcement:
    """Test: Access control prevents one user from viewing another user's ticket."""

    def test_access_control_enforcement(
        self, integration_setup, mock_gemini_model, mock_create_react_agent
    ):
        """
        Test workflow:
        1. Alice creates a ticket
        2. Bob tries to check Alice's ticket using its ID
        3. Verify Bob gets "not found" or "access" error message
        """
        # Create agents for alice and bob
        alice = HelpDeskAgent(user_email="alice@company.com")
        bob = HelpDeskAgent(user_email="bob@company.com")

        # Step 1: Alice creates a ticket
        alice_response = alice.run("Create a ticket for my laptop not working")

        # Extract ticket ID
        ticket_id_match = re.search(r"Ticket ID: ([a-f0-9\-]+)", alice_response)
        assert ticket_id_match, f"Could not extract ticket ID from Alice's response"
        ticket_id = ticket_id_match.group(1)

        # Verify Alice's ticket is in storage
        alice_ticket = integration_setup.get_ticket(ticket_id, "alice@company.com")
        assert alice_ticket is not None, "Alice's ticket not found in storage"

        # Step 2: Bob tries to check Alice's ticket
        bob_response = bob.run(f"Check status of ticket {ticket_id}")

        # Step 3: Verify Bob gets an access error
        # The response should contain "not found" or "access denied" or similar
        assert (
            "not found" in bob_response.lower()
            or "access" in bob_response.lower()
            or "denied" in bob_response.lower()
        ), (
            f"Expected access control error, but got: {bob_response}"
        )

        # Verify the ticket is still NOT accessible to bob in storage
        bob_ticket = integration_setup.get_ticket(ticket_id, "bob@company.com")
        assert bob_ticket is None, "Bob should not be able to access Alice's ticket"


class TestMultipleTicketsPerUser:
    """Test: Users can create and manage multiple tickets."""

    def test_multiple_tickets_per_user(
        self, integration_setup, mock_gemini_model, mock_create_react_agent
    ):
        """
        Test workflow:
        1. Agent creates first ticket via run("Create ticket for VPN issue")
        2. Agent creates second ticket via run("Create ticket for printer issue")
        3. Verify both tickets exist in storage for that user
        4. Verify only 2 tickets for the user, not for other users
        """
        # Create agent for charlie
        charlie = HelpDeskAgent(user_email="charlie@company.com")

        # Step 1: Create first ticket
        response1 = charlie.run("Create a ticket for my VPN issue")

        ticket_id_match1 = re.search(r"Ticket ID: ([a-f0-9\-]+)", response1)
        assert ticket_id_match1, f"Could not extract ticket ID from first ticket response"
        ticket_id_1 = ticket_id_match1.group(1)

        # Step 2: Create second ticket
        response2 = charlie.run("Create a ticket for my printer issue")

        ticket_id_match2 = re.search(r"Ticket ID: ([a-f0-9\-]+)", response2)
        assert ticket_id_match2, f"Could not extract ticket ID from second ticket response"
        ticket_id_2 = ticket_id_match2.group(1)

        # Verify both ticket IDs are different
        assert ticket_id_1 != ticket_id_2, "Two tickets should have different IDs"

        # Step 3: Verify both tickets exist in storage
        ticket_1 = integration_setup.get_ticket(ticket_id_1, "charlie@company.com")
        ticket_2 = integration_setup.get_ticket(ticket_id_2, "charlie@company.com")

        assert ticket_1 is not None, "First ticket not found in storage"
        assert ticket_2 is not None, "Second ticket not found in storage"

        # Step 4: Verify only 2 tickets for charlie (not for other users)
        charlie_tickets = integration_setup.list_user_tickets("charlie@company.com")
        assert len(charlie_tickets) == 2, f"Expected 2 tickets for charlie, got {len(charlie_tickets)}"

        # Verify the tickets have correct titles
        charlie_ticket_titles = {t.title for t in charlie_tickets}
        assert "VPN Access Issue" in charlie_ticket_titles, "First ticket title not found"
        assert "Support Request" in charlie_ticket_titles, "Second ticket title not found"

        # Verify no tickets exist for other users
        other_user_tickets = integration_setup.list_user_tickets("dave@company.com")
        assert len(other_user_tickets) == 0, "Should be no tickets for dave"
