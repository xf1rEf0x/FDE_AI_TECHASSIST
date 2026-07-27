"""LangChain integration for HuggingFace models."""

import os
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_google_genai import ChatGoogleGenerativeAI
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


def get_gemini_api_key() -> str:
    """Load GOOGLE_API_KEY from .env or environment.

    Returns:
        Gemini API key

    Raises:
        ValueError: If key is not found
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found. Please set it in .env or environment variables."
        )
    return api_key


def create_langchain_model(temperature: float = 0.7, provider: str = "huggingface"):
    """Initialize LLM model via LangChain based on chosen provider.

    Args:
        temperature: Model temperature (0.0 - 2.0)
        provider: "huggingface" or "gemini" (case-insensitive)

    Returns:
        LLM instance (ChatHuggingFace or ChatGoogleGenerativeAI) compatible with LCEL chains

    Raises:
        ValueError: If provider is unknown or API key is missing
    """
    provider = provider.lower().strip()

    if provider == "huggingface":
        api_key = get_huggingface_api_key()
        hf_llm = HuggingFaceEndpoint(
            repo_id="deepseek-ai/DeepSeek-R1:novita",
            huggingfacehub_api_token=api_key,
            temperature=temperature,
        )
        model = ChatHuggingFace(llm=hf_llm)
        return model

    elif provider == "gemini":
        api_key = get_gemini_api_key()
        model = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=temperature,
            google_api_key=api_key,
        )
        return model

    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'huggingface' or 'gemini'.")


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
