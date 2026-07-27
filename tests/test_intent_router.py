"""Tests for IntentRouter intent detection."""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from src.intent_router import IntentRouter


@pytest.fixture
def mock_chat_model():
    """Fixture: mock ChatGoogleGenerativeAI to avoid API key requirement."""
    with patch("src.intent_router.ChatGoogleGenerativeAI") as mock_model_class:
        mock_instance = MagicMock()
        
        def mock_invoke(prompt):
            """Mock invoke that returns appropriate intent based on prompt content."""
            user_msg = prompt.split('User message: "')[1].split('"')[0] if 'User message: "' in prompt else ""
            
            # Check exact messages first
            if "My laptop screen is broken" in user_msg or "broken, can you create a ticket" in user_msg:
                return AIMessage(content='{"intent": "helpdesk", "confidence": 0.95, "clarification": null}')
            elif "Microsoft Office license" in user_msg:
                return AIMessage(content='{"intent": "software_request", "confidence": 0.92, "clarification": null}')
            elif "Show me my assigned laptop" in user_msg:
                return AIMessage(content='{"intent": "asset_search", "confidence": 0.88, "clarification": null}')
            elif "Help!" in user_msg:
                return AIMessage(content='{"intent": "unknown", "confidence": 0.3, "clarification": "I\'m not sure what you need."}')
            else:
                return AIMessage(content='{"intent": "unknown", "confidence": 0.0, "clarification": "I\'m not sure what you need."}')
        
        mock_instance.invoke = mock_invoke
        mock_model_class.return_value = mock_instance
        yield mock_model_class


@pytest.fixture
def router(mock_chat_model):
    """Fixture: IntentRouter instance with mocked model."""
    return IntentRouter()


class TestIntentDetection:
    """Tests for intent detection functionality."""

    def test_helpdesk_intent_detection(self, router):
        """Test: Detect helpdesk intent from ticket-related message."""
        result = router.detect_intent("My laptop screen is broken, can you create a ticket?", [])
        assert result["intent"] == "helpdesk"
        assert result["confidence"] > 0.7

    def test_software_request_intent_detection(self, router):
        """Test: Detect software_request intent from license/install message."""
        result = router.detect_intent("I need to request Microsoft Office license", [])
        assert result["intent"] == "software_request"
        assert result["confidence"] > 0.7

    def test_asset_search_intent_detection(self, router):
        """Test: Detect asset_search intent from asset lookup message."""
        result = router.detect_intent("Show me my assigned laptop", [])
        assert result["intent"] == "asset_search"
        assert result["confidence"] > 0.7

    def test_ambiguous_intent_detection(self, router):
        """Test: Return clarification for ambiguous intent."""
        result = router.detect_intent("Help!", [])
        assert result["clarification"] is not None
        # When clarification is present, intent should be unknown or low confidence
        assert result["intent"] == "unknown" or result["confidence"] < 0.7
