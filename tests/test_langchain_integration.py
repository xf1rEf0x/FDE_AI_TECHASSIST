"""Unit tests for LangChain integration module."""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Mock the langchain.chains module before importing
sys.modules['langchain.chains'] = MagicMock()
sys.modules['langchain'] = MagicMock()

from src.langchain_integration import (
    get_huggingface_api_key,
    create_langchain_model,
    build_prompt_template,
    create_conversation_chain,
)

load_dotenv()


class TestHuggingFaceAPI:
    """Tests for HuggingFace API key retrieval."""

    def test_get_huggingface_api_key_exists(self):
        """Test that HuggingFace API key is loaded from .env."""
        api_key = get_huggingface_api_key()
        assert isinstance(api_key, str)
        assert len(api_key) > 0

    def test_get_huggingface_api_key_not_empty(self):
        """Test that API key is not empty."""
        api_key = get_huggingface_api_key()
        assert api_key.strip() != ""


class TestLangChainModel:
    """Tests for LangChain model initialization."""

    @patch('src.langchain_integration.ChatHuggingFace')
    def test_create_langchain_model_default_temperature(self, mock_chat):
        """Test model creation with default temperature."""
        mock_model = MagicMock()
        mock_model.temperature = 0.7
        mock_chat.return_value = mock_model

        model = create_langchain_model()
        assert model is not None
        assert hasattr(model, 'temperature')

    @patch('src.langchain_integration.ChatHuggingFace')
    def test_create_langchain_model_custom_temperature(self, mock_chat):
        """Test model creation with custom temperature."""
        mock_model = MagicMock()
        mock_model.temperature = 1.5
        mock_chat.return_value = mock_model

        model = create_langchain_model(temperature=1.5)
        assert model is not None


class TestPromptTemplate:
    """Tests for prompt template building."""

    def test_build_prompt_template(self):
        """Test creating a chat prompt template."""
        system_prompt = "You are a helpful assistant."
        template = build_prompt_template(system_prompt)
        assert template is not None
        assert hasattr(template, 'format_messages')


class TestConversationChain:
    """Tests for conversation chain creation."""

    @patch('src.langchain_integration.create_langchain_model')
    def test_create_conversation_chain(self, mock_create_model):
        """Test creating a complete conversation chain."""
        mock_model = MagicMock()
        mock_create_model.return_value = mock_model

        system_prompt = "You are a helpful IT support assistant."
        chain = create_conversation_chain(system_prompt, temperature=0.7)
        assert chain is not None
