"""Integration tests for conversation module."""

import pytest
from unittest.mock import patch, MagicMock
from src.conversation import get_response, initialize_client


@pytest.mark.parametrize("role", ["employee", "engineer", "admin"])
def test_get_response_with_valid_role(role, mock_gemini_client):
    """Verify get_response works with all valid roles."""
    with patch("src.conversation.initialize_client", return_value=mock_gemini_client):
        response = get_response("Hello", role, [])
        assert response is not None
        assert len(response) > 0


def test_get_response_with_history(mock_gemini_client):
    """Verify get_response includes conversation history."""
    history = [
        {"role": "user", "content": "What's the password policy?"},
        {"role": "assistant", "content": "Our policy requires..."},
    ]

    with patch("src.conversation.initialize_client", return_value=mock_gemini_client):
        response = get_response("Can you summarize that?", "admin", history)
        assert response is not None
        assert len(response) > 0


def test_get_response_empty_message_raises_error(mock_gemini_client):
    """Verify empty message raises ValueError."""
    with patch("src.conversation.initialize_client", return_value=mock_gemini_client):
        with pytest.raises(ValueError, match="cannot be empty"):
            get_response("", "employee", [])


def test_get_response_whitespace_message_raises_error(mock_gemini_client):
    """Verify whitespace-only message raises ValueError."""
    with patch("src.conversation.initialize_client", return_value=mock_gemini_client):
        with pytest.raises(ValueError, match="cannot be empty"):
            get_response("   ", "employee", [])


def test_get_response_invalid_role(mock_gemini_client):
    """Verify invalid role raises ValueError."""
    with patch("src.conversation.initialize_client", return_value=mock_gemini_client):
        with pytest.raises(ValueError, match="Unknown role"):
            get_response("Hello", "invalid_role", [])


@patch("src.conversation.genai.Client")
@patch("src.conversation.get_api_key")
def test_initialize_client_with_api_key(mock_get_key, mock_client_class):
    """Verify client initializes with API key."""
    mock_get_key.return_value = "test_key"
    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance

    client = initialize_client()

    mock_client_class.assert_called_once_with(api_key="test_key")
    assert client == mock_client_instance


@patch("src.conversation.get_api_key")
def test_initialize_client_missing_api_key(mock_get_key):
    """Verify missing API key raises error."""
    mock_get_key.side_effect = ValueError("GOOGLE_API_KEY not found")

    with pytest.raises(ValueError, match="GOOGLE_API_KEY not found"):
        initialize_client()
