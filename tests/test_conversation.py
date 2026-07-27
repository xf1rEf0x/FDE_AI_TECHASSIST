"""Tests for LangChain-based conversation module."""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from src.conversation import get_response, get_response_stream
from src.prompts import get_available_roles


class TestGetResponse:
    """Tests for get_response function."""

    @patch('src.conversation.create_langchain_model')
    def test_get_response_valid_input(self, mock_model):
        """Test get_response with valid user message and role."""
        # Create a mock model that returns an AIMessage
        mock_llm = MagicMock()
        mock_response = AIMessage(content="This is a test response.")
        mock_llm.invoke.return_value = mock_response
        mock_model.return_value = mock_llm

        with patch('src.conversation.ChatPromptTemplate.from_messages') as mock_prompt:
            # Create a mock prompt that supports the pipe operator
            mock_prompt_obj = MagicMock()
            mock_prompt_obj.__or__ = lambda self, other: mock_llm
            mock_prompt.return_value = mock_prompt_obj

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
        mock_llm = MagicMock()
        mock_response = AIMessage(content=f"Response for {role}")
        mock_llm.invoke.return_value = mock_response
        mock_model.return_value = mock_llm

        with patch('src.conversation.ChatPromptTemplate.from_messages') as mock_prompt:
            mock_prompt_obj = MagicMock()
            mock_prompt_obj.__or__ = lambda self, other: mock_llm
            mock_prompt.return_value = mock_prompt_obj

            response = get_response("Test", role, [])
            assert isinstance(response, str)
            assert response == f"Response for {role}"


class TestGetResponseStream:
    """Tests for get_response_stream function."""

    @patch('src.conversation.create_langchain_model')
    def test_get_response_stream_valid_input(self, mock_model):
        """Test get_response_stream yields text chunks."""
        mock_llm = MagicMock()
        mock_response = AIMessage(content="This is a streamed response.")
        mock_llm.invoke.return_value = mock_response
        mock_model.return_value = mock_llm

        with patch('src.conversation.ChatPromptTemplate.from_messages') as mock_prompt:
            mock_prompt_obj = MagicMock()
            mock_prompt_obj.__or__ = lambda self, other: mock_llm
            mock_prompt.return_value = mock_prompt_obj

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
