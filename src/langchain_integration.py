"""LangChain integration for HuggingFace models."""

import os
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_huggingface import ChatHuggingFace
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

    model = ChatHuggingFace(
        huggingface_api_key=api_key,
        model_name="mistralai/Mistral-7B-Instruct-v0.1",  # ponytail: swap model name if HF inference endpoint changes
        temperature=temperature,
    )
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
        LangChain LLMChain ready for invoke() calls
    """
    from langchain.chains import LLMChain

    model = create_langchain_model(temperature)
    prompt_template = build_prompt_template(system_prompt)

    chain = LLMChain(llm=model, prompt=prompt_template)
    return chain
