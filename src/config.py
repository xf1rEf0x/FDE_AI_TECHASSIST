import os
from dotenv import load_dotenv

load_dotenv()

def get_api_key() -> str:
    """Load GOOGLE_API_KEY from .env or environment."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found. Please set it in .env or environment variables."
        )
    return api_key


def get_gemini_model() -> str:
    """Get Gemini model name. Defaults to gemini-3.5-flash-lite."""
    return os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def get_available_models() -> list[str]:
    """Get list of available Gemini models."""
    return [
        "gemini-3.5-flash-lite",
        "gemma-4-31b-it",
    ]


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
