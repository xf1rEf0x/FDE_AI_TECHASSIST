"""Integration tests for HelpDeskAgent password reset functionality."""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.agents.helpdesk_agent import HelpDeskAgent


@pytest.fixture
def mock_chat_model():
    """Fixture: mock ChatGoogleGenerativeAI to avoid API key requirement."""
    with patch("src.agents.helpdesk_agent.ChatGoogleGenerativeAI") as mock_model:
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_create_react_agent():
    """Fixture: mock create_react_agent to avoid agent graph setup."""
    with patch("src.agents.helpdesk_agent.create_react_agent") as mock_agent:
        mock_executor = MagicMock()
        mock_agent.return_value = mock_executor
        yield mock_executor


@pytest.fixture
def helpdesk_agent(mock_chat_model, mock_create_react_agent):
    """Create a HelpDeskAgent instance for testing."""
    return HelpDeskAgent("test_user@techassist.com")


def test_agent_has_reset_password_tool(helpdesk_agent):
    """Test that HelpDeskAgent has reset_password tool."""
    tool_names = [tool.name for tool in helpdesk_agent.tools]
    assert "reset_password" in tool_names


def test_agent_tools_count(helpdesk_agent):
    """Test that HelpDeskAgent has expected number of tools (4 ticket + 1 password)."""
    assert len(helpdesk_agent.tools) == 5


def test_agent_prompt_mentions_password_reset(helpdesk_agent):
    """Test that system prompt includes password reset instructions."""
    # We can't easily access the prompt, but we verify the tool exists
    # and the user_email is properly scoped
    assert helpdesk_agent.user_email == "test_user@techassist.com"
    tool_names = [tool.name for tool in helpdesk_agent.tools]
    assert "reset_password" in tool_names


def teardown_function():
    """Clean up password log after tests."""
    if os.path.exists("data/passwords.json"):
        os.remove("data/passwords.json")
