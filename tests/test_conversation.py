"""Tests for LangChain-based conversation module."""

import pytest
from unittest.mock import patch, MagicMock
from src.conversation import get_response, get_response_stream
from src.prompts import get_available_roles


class TestGetResponse:
    """Tests for get_response function."""

    @patch('src.conversation.create_langchain_model')
    def test_get_response_valid_input(self, mock_model):
        """Test get_response with valid user message and role."""
        mock_response = MagicMock()
        mock_response.content = "This is a test response."
        mock_model.return_value = mock_response

        with patch('src.conversation.ChatPromptTemplate.from_messages') as mock_prompt:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            # Simulate the pipe operator behavior
            mock_prompt.return_value.__or__.return_value = mock_chain

            response = get_response("Hello", "employee", [], temperature=0.7)
            assert response == "This is a test response."

    def test_get_response_empty_message_raises_error(self):
        """Test that empty user message raises ValueError."""
        with pytest.raises(ValueError, match="User message cannot be empty"):
            get_response("", "employee", [])

    def test_get_response_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Unknown role"):
            get_response("Hello", "invalid_role", [])

    @pytest.mark.parametrize("role", get_available_roles())
    @patch('src.conversation.create_langchain_model')
    def test_get_response_all_roles(self, mock_model, role):
        """Test get_response works with all available roles."""
        mock_response = MagicMock()
        mock_response.content = f"Response for {role}"
        mock_model.return_value = mock_response

        with patch('src.conversation.ChatPromptTemplate.from_messages') as mock_prompt:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            mock_prompt.return_value.__or__.return_value = mock_chain

            response = get_response("Test", role, [])
            assert isinstance(response, str)


class TestGetResponseStream:
    """Tests for get_response_stream function."""

    @patch('src.conversation.create_langchain_model')
    def test_get_response_stream_valid_input(self, mock_model):
        """Test get_response_stream yields text chunks."""
        mock_response = MagicMock()
        mock_response.content = "This is a streamed response."
        mock_model.return_value = mock_response

        with patch('src.conversation.ChatPromptTemplate.from_messages') as mock_prompt:
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            mock_prompt.return_value.__or__.return_value = mock_chain

            chunks = list(get_response_stream("Hello", "employee", []))
            assert len(chunks) > 0
            assert "".join(chunks) == "This is a streamed response."

    def test_get_response_stream_empty_message_raises_error(self):
        """Test that empty user message raises ValueError."""
        with pytest.raises(ValueError, match="User message cannot be empty"):
            list(get_response_stream("", "employee", []))

    def test_get_response_stream_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Unknown role"):
            list(get_response_stream("Hello", "invalid_role", []))
