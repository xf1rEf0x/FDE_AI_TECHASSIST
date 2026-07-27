"""Shared test fixtures and mocks."""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage


@pytest.fixture
def mock_hf_response():
    """Mock HuggingFace API responses by role and intent."""
    responses = {
        ("employee", "password"): "To reset your password:\n1. Go to the IT Portal (portal.company.com)\n2. Click 'Reset Password'\n3. Follow the instructions\n\nIf you have issues, contact the helpdesk.",
        ("employee", "vpn"): "To access VPN:\n1. Download the VPN client\n2. Enter your credentials\n3. Connect to the office network\n\nFor setup help, see the IT knowledge base.",
        ("engineer", "password"): "LDAP password reset API: POST /api/v1/password-reset with employee_id and temporary_token. Requires MFA validation before API call.",
        ("engineer", "vpn"): "VPN uses OpenVPN protocol. Config in /etc/openvpn/client.conf. Check routing table: 'ip route show'. Debug with: 'openvpn --log verbose.log'",
        ("admin", "password"): "Password policy: 12+ chars, uppercase, lowercase, number, symbol. Reset requires MFA + audit log entry. Compliance: SOC 2, HIPAA.",
        ("admin", "vpn"): "VPN audit: log all connections in syslog. Review quarterly. MFA mandatory. Compliance: NIST 800-171.",
    }

    def get_response(user_message, role="employee"):
        intent = "password" if "password" in user_message.lower() else "vpn" if "vpn" in user_message.lower() else "general"
        key = (role, intent)
        return responses.get(key, f"I can help with that as a {role}.")

    return get_response


@pytest.fixture
def mock_hf_chat_model(mock_hf_response):
    """Mock the HuggingFace chat model (ChatHuggingFace)."""
    with patch("src.langchain_integration.ChatHuggingFace") as mock_model_class:
        def mock_invoke(input_dict):
            user_input = input_dict.get("user_input", "")
            # Extract role from system prompt if available
            role = "employee"
            return AIMessage(content=mock_hf_response(user_input, role))

        mock_instance = MagicMock()
        mock_instance.invoke = mock_invoke
        # Make the pipe operator return a mock chain that can be invoked
        def mock_pipe_op(other):
            chain_mock = MagicMock()
            chain_mock.invoke = mock_invoke
            return chain_mock
        mock_instance.__or__ = mock_pipe_op
        mock_model_class.return_value = mock_instance

        yield mock_instance


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
