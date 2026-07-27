import os
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
