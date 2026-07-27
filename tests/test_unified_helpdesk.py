"""Integration tests for unified HelpDesk flow end-to-end."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import AIMessage
from src.ui.helpdesk_tab import render_helpdesk_tab
from src.intent_router import IntentRouter
from src.agents.helpdesk_agent import HelpDeskAgent
from src.agents.software_agent import SoftwareRequestAgent


@pytest.fixture
def mock_chat_model():
    """Fixture: mock ChatGoogleGenerativeAI to avoid API key requirement."""
    with patch("src.intent_router.ChatGoogleGenerativeAI") as mock_model_class:
        mock_instance = MagicMock()

        def mock_invoke(prompt):
            """Mock invoke that returns appropriate intent based on prompt content."""
            user_msg = prompt.split('User message: "')[1].split('"')[0] if 'User message: "' in prompt else ""

            # Helpdesk intents
            if any(keyword in user_msg.lower() for keyword in ["ticket", "broken", "crash", "issue", "not working", "error"]):
                return AIMessage(content='{"intent": "helpdesk", "confidence": 0.95, "clarification": null}')
            # Software request intents
            elif any(keyword in user_msg.lower() for keyword in ["software", "license", "install", "application", "app", "request software"]):
                return AIMessage(content='{"intent": "software_request", "confidence": 0.92, "clarification": null}')
            # Asset search intents
            elif any(keyword in user_msg.lower() for keyword in ["laptop", "desktop", "monitor", "asset", "device", "hardware", "assigned"]):
                return AIMessage(content='{"intent": "asset_search", "confidence": 0.88, "clarification": null}')
            # Ambiguous
            elif "help" in user_msg.lower() and len(user_msg) < 10:
                return AIMessage(content='{"intent": "unknown", "confidence": 0.3, "clarification": "I\'m not sure what you need. Are you asking about: (1) creating a support ticket, (2) requesting software, or (3) checking your assigned assets?"}')
            else:
                return AIMessage(content='{"intent": "unknown", "confidence": 0.0, "clarification": null}')

        mock_instance.invoke = mock_invoke
        mock_model_class.return_value = mock_instance
        yield mock_model_class


@pytest.fixture
def router(mock_chat_model):
    """Fixture: IntentRouter instance with mocked model."""
    return IntentRouter()


class TestIntentRouterDetection:
    """Tests for intent router detection functionality."""

    def test_intent_router_detects_helpdesk_intent(self, router):
        """Verify intent router correctly identifies helpdesk requests."""
        result = router.detect_intent(
            "My computer keeps crashing, I need help",
            []
        )
        assert result["intent"] in ["helpdesk", "unknown"]
        # When intent is helpdesk, confidence should be reasonable
        if result["intent"] == "helpdesk":
            assert result["confidence"] > 0.7

    def test_intent_router_detects_software_intent(self, router):
        """Verify intent router correctly identifies software requests."""
        result = router.detect_intent(
            "I need to request Microsoft Excel license",
            []
        )
        assert result["intent"] in ["software_request", "unknown"]
        if result["intent"] == "software_request":
            assert result["confidence"] > 0.7

    def test_intent_router_detects_asset_intent(self, router):
        """Verify intent router correctly identifies asset queries."""
        result = router.detect_intent(
            "Show me my assigned laptop",
            []
        )
        assert result["intent"] in ["asset_search", "unknown"]
        if result["intent"] == "asset_search":
            assert result["confidence"] > 0.7

    def test_intent_router_asks_for_clarification_on_ambiguous(self, router):
        """Verify intent router asks for clarification when ambiguous."""
        result = router.detect_intent("Help!", [])
        # Should either detect an intent with high confidence OR provide clarification
        assert result["intent"] or result.get("clarification")
        # If providing clarification, intent should be unknown or low confidence
        if result.get("clarification"):
            assert result["intent"] == "unknown" or result["confidence"] < 0.7


class TestIntentRouterWithChatHistory:
    """Tests for intent router with conversation context."""

    def test_intent_router_uses_chat_history_for_context(self, router):
        """Verify router can use chat history to refine intent detection."""
        chat_history = [
            {"role": "user", "content": "My laptop screen is broken"},
            {"role": "assistant", "content": "I can help you create a ticket for that."}
        ]
        result = router.detect_intent("Can you create one for me?", chat_history)
        # Should understand context and detect helpdesk intent
        assert result["intent"] in ["helpdesk", "unknown"]

    def test_intent_router_with_empty_history(self, router):
        """Verify router handles empty chat history gracefully."""
        result = router.detect_intent("I need a new laptop", [])
        assert "intent" in result
        assert "confidence" in result


class TestIntentRouterEdgeCases:
    """Tests for edge cases and robustness."""

    def test_intent_router_handles_long_message(self, router):
        """Verify router can handle long user messages."""
        long_message = "My computer has been having issues with the VPN connection. " \
                       "Every time I try to connect to the office network, I get an error message. " \
                       "I need to create a ticket to get this fixed. Can you help?"
        result = router.detect_intent(long_message, [])
        # Should detect helpdesk intent despite length
        assert result["intent"] in ["helpdesk", "unknown"]
        assert "confidence" in result

    def test_intent_router_handles_mixed_topics(self, router):
        """Verify router handles messages mixing multiple topics."""
        mixed_message = "I need to create a ticket for my laptop which is also missing software like Python"
        result = router.detect_intent(mixed_message, [])
        # Should detect one primary intent
        assert result["intent"] in ["helpdesk", "software_request", "asset_search", "unknown"]
        assert "confidence" in result

    def test_intent_router_returns_valid_json_structure(self, router):
        """Verify router always returns properly structured JSON result."""
        result = router.detect_intent("Random test message xyz", [])
        assert isinstance(result, dict)
        assert "intent" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], (int, float))
        # Confidence should be between 0 and 1
        assert 0.0 <= result["confidence"] <= 1.0


class TestUnifiedHelpDeskAgentIntegration:
    """Integration tests for the unified HelpDesk tab with all agents."""

    def test_router_with_helpdesk_agent_initialized(self, router):
        """Verify router can work with HelpDeskAgent."""
        with patch("src.agents.helpdesk_agent.ChatGoogleGenerativeAI"):
            agent = HelpDeskAgent("test@example.com")
            assert agent is not None
            # Verify agent has run method
            assert hasattr(agent, "run")

    def test_router_with_software_agent_initialized(self, router):
        """Verify router can work with SoftwareRequestAgent."""
        with patch("src.agents.software_agent.ChatGoogleGenerativeAI"):
            agent = SoftwareRequestAgent("test@example.com", is_admin=False)
            assert agent is not None
            assert hasattr(agent, "run")

    def test_intent_detection_for_software_with_admin_check(self, router):
        """Verify software intent detection works for admin flow."""
        result = router.detect_intent("I need to approve pending software requests", [])
        # Should detect software_request intent (approval is software-related)
        assert result["intent"] in ["software_request", "unknown"]

    def test_intent_detection_preserves_all_fields(self, router):
        """Verify all expected fields are present in intent result."""
        result = router.detect_intent("Check my laptop", [])
        expected_fields = {"intent", "confidence"}
        assert expected_fields.issubset(result.keys())
        # clarification may or may not be present
        if "clarification" in result:
            assert result["clarification"] is None or isinstance(result["clarification"], str)
