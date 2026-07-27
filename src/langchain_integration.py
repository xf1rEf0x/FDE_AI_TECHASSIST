"""LangChain integration for HuggingFace models."""

import os
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from dotenv import load_dotenv

load_dotenv()


def get_huggingface_api_key() -> str:
    """Load HUGGING_FACE_API from .env or environment.

    Returns:
        HuggingFace API key

    Raises:
        ValueError: If key is not found
    """
    api_key = os.getenv("HUGGING_FACE_API")
    if not api_key:
        raise ValueError(
            "HUGGING_FACE_API not found. Please set it in .env or environment variables."
        )
    return api_key


def create_langchain_model(temperature: float = 0.7) -> ChatHuggingFace:
    """Initialize HuggingFace chat model via LangChain.

    Args:
        temperature: Model temperature (0.0 - 2.0)

    Returns:
        ChatHuggingFace instance configured with temperature

    Raises:
        ValueError: If HuggingFace API key is not set
    """
    api_key = get_huggingface_api_key()

    # Create HuggingFaceEndpoint first (the base LLM)
    hf_llm = HuggingFaceEndpoint(
        repo_id="deepseek-ai/DeepSeek-R1:novita",
        huggingfacehub_api_token=api_key,
        temperature=temperature,
    )

    # Wrap in ChatHuggingFace for chat-specific behavior
    model = ChatHuggingFace(llm=hf_llm)
    return model


def build_prompt_template(system_prompt: str) -> ChatPromptTemplate:
    """Build a chat prompt template with system instruction.

    Args:
        system_prompt: System instruction text for the role

    Returns:
        ChatPromptTemplate combining system and user messages
    """
    system_message = SystemMessagePromptTemplate.from_template(system_prompt)
    human_message = HumanMessagePromptTemplate.from_template("{user_input}")

    chat_prompt = ChatPromptTemplate.from_messages([system_message, human_message])
    return chat_prompt


def create_conversation_chain(system_prompt: str, temperature: float = 0.7):
    """Create a LangChain conversation chain with system prompt.

    Args:
        system_prompt: System instruction for the role
        temperature: Model temperature

    Returns:
        LCEL chain (prompt | model) ready for invoke() calls
    """
    model = create_langchain_model(temperature)
    prompt_template = build_prompt_template(system_prompt)

    # Use LCEL (pipe) composition instead of deprecated LLMChain
    chain = prompt_template | model
    return chain
