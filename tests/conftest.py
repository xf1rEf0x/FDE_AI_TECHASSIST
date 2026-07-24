"""Shared test fixtures and mocks."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API responses by role and intent."""
    responses = {
        ("employee", "password"): "To reset your password:\n1. Go to the IT Portal (portal.company.com)\n2. Click 'Reset Password'\n3. Follow the instructions\n\nIf you have issues, contact the helpdesk.",
        ("employee", "vpn"): "To access VPN:\n1. Download the VPN client\n2. Enter your credentials\n3. Connect to the office network\n\nFor setup help, see the IT knowledge base.",
        ("engineer", "password"): "LDAP password reset API: POST /api/v1/password-reset with employee_id and temporary_token. Requires MFA validation before API call.",
        ("engineer", "vpn"): "VPN uses OpenVPN protocol. Config in /etc/openvpn/client.conf. Check routing table: 'ip route show'. Debug with: 'openvpn --log verbose.log'",
        ("admin", "password"): "Password policy: 12+ chars, uppercase, lowercase, number, symbol. Reset requires MFA + audit log entry. Compliance: SOC 2, HIPAA.",
        ("admin", "vpn"): "VPN audit: log all connections in syslog. Review quarterly. MFA mandatory. Compliance: NIST 800-171.",
    }

    def get_response(user_message, system_prompt=None):
        # Extract role and intent from system prompt and message
        role = "employee"
        for r in ["engineer", "admin"]:
            if r in system_prompt.lower() if system_prompt else False:
                role = r
                break

        intent = "password" if "password" in user_message.lower() else "vpn" if "vpn" in user_message.lower() else "general"

        key = (role, intent)
        return responses.get(key, f"I can help with that as a {role}.")

    return get_response


@pytest.fixture
def mock_gemini_client(mock_gemini_response):
    """Mock the Gemini client."""
    with patch("src.conversation.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the chat object
        mock_chat = MagicMock()
        mock_chat.system_instruction = ""

        def mock_send_message(message):
            response_mock = MagicMock()
            system_instruction = mock_chat.system_instruction if hasattr(mock_chat, 'system_instruction') else ""
            response_text = mock_gemini_response(message, system_instruction)
            response_mock.text = response_text

            # Return generator for streaming support
            def response_generator():
                yield response_mock

            return response_generator()

        mock_chat.send_message = mock_send_message
        mock_client.chats.create = MagicMock(return_value=mock_chat)

        yield mock_client


@pytest.fixture
def session_state():
    """Fixture: empty session state dict."""
    return {
        "role": "employee",
        "messages": [],
    }


@pytest.fixture
def sample_history():
    """Fixture: sample conversation history."""
    return [
        {"role": "user", "content": "What's the password policy?"},
        {"role": "assistant", "content": "Our password policy requires 12+ characters..."},
    ]
