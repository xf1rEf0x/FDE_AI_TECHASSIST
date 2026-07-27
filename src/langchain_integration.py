"""LangChain integration for HuggingFace models."""

import os
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import get_huggingface_api_key


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
            model="gemini-3.5-flash-lite",
            temperature=temperature,
            google_api_key=api_key,
        )
        return model

    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'huggingface' or 'gemini'.")


