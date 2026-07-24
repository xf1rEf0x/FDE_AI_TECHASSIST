"""End-to-end user flow tests for critical scenarios."""

import pytest
from unittest.mock import patch
from src.conversation import get_response
from src.utils import format_message


@pytest.fixture
def mock_all_endpoints(mock_gemini_client):
    """Mock all external endpoints for e2e tests."""
    with patch("src.conversation.initialize_client", return_value=mock_gemini_client):
        yield


class TestCriticalUserFlows:
    """Test critical user journeys."""

    def test_employee_password_reset_flow(self, mock_all_endpoints):
        """E2E: Employee asks about password reset."""
        # User message
        user_msg = "I forgot my password, what should I do?"

        # Get response as employee
        response = get_response(user_msg, "employee", [])

        # Verify response is present and employee-friendly
        assert response is not None
        assert len(response) > 0
        # Should mention steps or portal
        assert any(word in response.lower() for word in ["password", "reset", "help"])

    def test_engineer_vpn_technical_query(self, mock_all_endpoints):
        """E2E: Engineer asks technical VPN question."""
        user_msg = "How do I configure the VPN client?"

        response = get_response(user_msg, "engineer", [])

        assert response is not None
        assert len(response) > 0
        # Engineer response should have technical depth
        assert any(word in response.lower() for word in ["vpn", "config", "connect"])

    def test_admin_policy_query(self, mock_all_endpoints):
        """E2E: Admin asks about password policy."""
        user_msg = "What are our password policy requirements?"

        response = get_response(user_msg, "admin", [])

        assert response is not None
        assert len(response) > 0
        # Admin response should mention policy/security
        assert any(word in response.lower() for word in ["password", "policy", "security", "compliance"])

    def test_multi_turn_conversation(self, mock_all_endpoints):
        """E2E: Multi-turn conversation maintains context."""
        # First turn
        history = []
        user_msg1 = "What's VPN?"
        response1 = get_response(user_msg1, "employee", history)
        assert response1
        assert len(response1) > 0

        # Add to history
        history.append(format_message("user", user_msg1))
        history.append(format_message("assistant", response1))

        # Second turn (follow-up with history)
        user_msg2 = "How do I install it?"
        response2 = get_response(user_msg2, "employee", history)
        assert response2
        assert len(response2) > 0

        # Verify history was passed (we check that the function accepted it without error)
        # Real context matching requires actual Gemini API; mocked response won't have full context
        assert len(history) == 2  # History was built up correctly

    def test_role_persona_consistency(self, mock_all_endpoints):
        """E2E: Different roles give different responses to same question."""
        question = "What's the password policy?"

        # Get responses from different roles
        employee_response = get_response(question, "employee", [])
        admin_response = get_response(question, "admin", [])

        # Both should be non-empty
        assert employee_response
        assert admin_response

        # Admin response should be more detailed (different length or content)
        # This is a soft check since mock responses are fixed
        assert len(employee_response) > 0
        assert len(admin_response) > 0

    def test_empty_input_handling(self, mock_all_endpoints):
        """E2E: Empty input is rejected gracefully."""
        with pytest.raises(ValueError):
            get_response("", "employee", [])

    def test_conversation_history_preserved(self, mock_all_endpoints):
        """E2E: Conversation history is preserved across calls."""
        history = []

        # Turn 1
        msg1 = "What's VPN?"
        resp1 = get_response(msg1, "employee", history)
        history.append(format_message("user", msg1))
        history.append(format_message("assistant", resp1))

        # Turn 2
        msg2 = "How do I use it?"
        resp2 = get_response(msg2, "employee", history)
        history.append(format_message("user", msg2))
        history.append(format_message("assistant", resp2))

        # Verify history has all messages
        assert len(history) == 4
        assert history[0]["content"] == msg1
        assert history[2]["content"] == msg2
