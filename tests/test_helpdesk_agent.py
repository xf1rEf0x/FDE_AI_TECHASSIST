"""Tests for HelpDeskAgent with tool calling."""

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


class TestHelpDeskAgent:
    """Tests for HelpDeskAgent initialization and basic functionality."""

    def test_agent_receives_user_email(self, mock_chat_model, mock_create_react_agent):
        """Test: Agent stores user_email correctly."""
        user_email = "alice@company.com"
        agent = HelpDeskAgent(user_email=user_email)
        assert agent.user_email == user_email

    def test_agent_can_be_initialized(self, mock_chat_model, mock_create_react_agent):
        """Test: Agent initializes without error."""
        user_email = "bob@company.com"
        agent = HelpDeskAgent(user_email=user_email)
        assert agent is not None
        assert hasattr(agent, "executor")
        assert callable(agent.run)
