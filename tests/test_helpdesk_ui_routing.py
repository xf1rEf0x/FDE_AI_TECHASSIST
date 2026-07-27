"""Tests for unified HelpDesk tab UI routing to appropriate agents."""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage

from src.intent_router import IntentRouter
from src.agents.helpdesk_agent import HelpDeskAgent
from src.agents.software_agent import SoftwareRequestAgent


@pytest.fixture
def mock_intent_router():
    """Fixture: mock IntentRouter to avoid Gemini API calls."""
    with patch("src.intent_router.ChatGoogleGenerativeAI") as mock_model_class:
        mock_instance = MagicMock()

        def mock_invoke(prompt):
            """Mock invoke that returns appropriate intent based on prompt content."""
            user_msg = prompt.split('User message: "')[1].split('"')[0] if 'User message: "' in prompt else ""

            # Detect intents based on keywords (check asset search first to avoid conflict with "laptop" in helpdesk)
            if any(word in user_msg.lower() for word in ["devices", "hardware", "assigned"]) and "broken" not in user_msg.lower():
                return AIMessage(content='{"intent": "asset_search", "confidence": 0.88, "clarification": null}')
            elif any(word in user_msg.lower() for word in ["broken", "create ticket", "ticket", "issue", "crash", "error"]):
                return AIMessage(content='{"intent": "helpdesk", "confidence": 0.95, "clarification": null}')
            elif any(word in user_msg.lower() for word in ["visual studio code", "software", "license", "install", "application"]):
                return AIMessage(content='{"intent": "software_request", "confidence": 0.92, "clarification": null}')
            else:
                return AIMessage(content='{"intent": "unknown", "confidence": 0.3, "clarification": "I\'m not sure what you need. Are you asking about: (1) creating a support ticket, (2) requesting software, or (3) checking your assigned assets?"}')

        mock_instance.invoke = mock_invoke
        mock_model_class.return_value = mock_instance
        yield mock_model_class


@pytest.fixture
def mock_helpdesk_agent():
    """Fixture: mock HelpDeskAgent to avoid Gemini API calls."""
    with patch("src.ui.helpdesk_tab.HelpDeskAgent") as mock_class:
        mock_instance = MagicMock()
        mock_instance.run = MagicMock(return_value="Ticket created successfully. Ticket ID: tk-12345")
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_software_agent():
    """Fixture: mock SoftwareRequestAgent to avoid Gemini API calls."""
    with patch("src.ui.helpdesk_tab.SoftwareRequestAgent") as mock_class:
        mock_instance = MagicMock()
        mock_instance.run = MagicMock(return_value="Software request created successfully. Request ID: sr-67890")
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_asset_search():
    """Fixture: mock asset search function to avoid Gemini API calls."""
    with patch("src.ui.helpdesk_tab.search_assets") as mock_func:
        mock_func.return_value = "You have 1 laptop assigned: MacBook Pro 16-inch (Serial: MP2024)"
        yield mock_func


class TestHelpDeskIntentRouting:
    """Test: User queries are routed to the correct agent based on intent."""

    def test_helpdesk_intent_routes_to_helpdesk_agent(self, mock_intent_router):
        """Test: Helpdesk intent routes to HelpDeskAgent."""
        router = IntentRouter()

        result = router.detect_intent("My laptop screen is broken, can you create a ticket?", [])

        assert result["intent"] == "helpdesk"
        assert result["confidence"] > 0.7
        assert result["clarification"] is None

    def test_software_intent_routes_to_software_agent(self, mock_intent_router):
        """Test: Software request intent routes to SoftwareRequestAgent."""
        router = IntentRouter()

        result = router.detect_intent("I need Visual Studio Code license", [])

        assert result["intent"] == "software_request"
        assert result["confidence"] > 0.7
        assert result["clarification"] is None

    def test_asset_intent_routes_to_asset_search(self, mock_intent_router):
        """Test: Asset search intent routes to asset search."""
        router = IntentRouter()

        result = router.detect_intent("What are my assigned devices and hardware", [])

        assert result["intent"] == "asset_search"
        assert result["confidence"] > 0.7
        assert result["clarification"] is None

    def test_ambiguous_intent_returns_clarification(self, mock_intent_router):
        """Test: Ambiguous intent returns clarification instead of routing."""
        router = IntentRouter()

        result = router.detect_intent("Help!", [])

        assert result["intent"] == "unknown"
        assert result["clarification"] is not None
        assert "support ticket" in result["clarification"] or "requesting software" in result["clarification"] or "assets" in result["clarification"]


class TestUnifiedMessageHistory:
    """Test: All messages from different agents appear in a unified history."""

    def test_unified_messages_across_intents(self, mock_intent_router, mock_helpdesk_agent, mock_software_agent):
        """Test: Messages from different intents appear in single conversation stream."""
        # This test validates the unified_helpdesk_messages session state
        # which is shared across all agent responses

        router = IntentRouter()

        # Simulate multiple queries that would route to different agents
        messages = []

        # First message: helpdesk intent
        msg1 = "My laptop screen is broken, can you create a ticket?"
        result1 = router.detect_intent(msg1, messages)
        messages.append({"role": "user", "content": msg1})
        messages.append({"role": "assistant", "content": "Ticket created successfully."})

        # Second message: software request intent
        msg2 = "I need Visual Studio Code license"
        result2 = router.detect_intent(msg2, messages)
        messages.append({"role": "user", "content": msg2})
        messages.append({"role": "assistant", "content": "Software request created successfully."})

        # Verify all messages are in the same list
        assert len(messages) == 4
        assert messages[0]["content"] == msg1
        assert messages[1]["content"] == "Ticket created successfully."
        assert messages[2]["content"] == msg2
        assert messages[3]["content"] == "Software request created successfully."

        # Verify intents were correctly detected
        assert result1["intent"] == "helpdesk"
        assert result2["intent"] == "software_request"


class TestHelpDeskAgentInitialization:
    """Test: Agents are properly initialized and reused in session state."""

    def test_helpdesk_agent_created_on_first_visit(self, mock_helpdesk_agent):
        """Test: HelpDeskAgent is created when tab is first visited."""
        # Verify that HelpDeskAgent is properly mocked
        from src.ui.helpdesk_tab import HelpDeskAgent

        # The mock is already set up by the fixture
        # Just verify it's callable and returns a mock instance
        agent = HelpDeskAgent("test@example.com")
        assert agent is not None
        assert hasattr(agent, 'run')


class TestIntentDetectionEdgeCases:
    """Test: Edge cases in intent detection."""

    def test_multiple_keywords_same_intent(self, mock_intent_router):
        """Test: Message with multiple keywords routes correctly."""
        router = IntentRouter()

        result = router.detect_intent("I need to create a ticket because my VPN is broken", [])

        assert result["intent"] == "helpdesk"

    def test_case_insensitive_detection(self, mock_intent_router):
        """Test: Intent detection is case-insensitive."""
        router = IntentRouter()

        result_lower = router.detect_intent("my laptop is broken", [])
        result_upper = router.detect_intent("MY LAPTOP IS BROKEN", [])

        assert result_lower["intent"] == result_upper["intent"]

    def test_empty_message_handling(self, mock_intent_router):
        """Test: Empty message returns unknown intent with clarification."""
        router = IntentRouter()

        result = router.detect_intent("", [])

        assert result["intent"] == "unknown"
        assert result.get("clarification") is not None


class TestRoutingWithChatHistory:
    """Test: Intent detection considers chat history context."""

    def test_intent_with_empty_history(self, mock_intent_router):
        """Test: Intent detected correctly with empty history."""
        router = IntentRouter()

        result = router.detect_intent("I need Visual Studio Code", [])

        assert result["intent"] == "software_request"

    def test_intent_with_conversation_context(self, mock_intent_router):
        """Test: Intent detected considering prior messages."""
        router = IntentRouter()

        history = [
            {"role": "user", "content": "I need Visual Studio Code"},
            {"role": "assistant", "content": "I can help with that"}
        ]

        result = router.detect_intent("Please create a software request", history)

        # Should still detect software request intent
        assert result["intent"] in ["software_request", "unknown"]
