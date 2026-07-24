"""Conversation handler for Gemini API integration."""

import google.genai as genai
from src.config import get_api_key, get_gemini_model
from src.prompts import get_system_prompt


def initialize_client() -> genai.Client:
    """Initialize and return Gemini API client."""
    api_key = get_api_key()
    return genai.Client(api_key=api_key)


def get_response(user_message: str, role: str, history: list[dict]) -> str:
    """Get response from Gemini API for a user message.

    Args:
        user_message: The user's latest message
        role: User role ("employee", "engineer", or "admin")
        history: List of previous messages in format [{"role": "user"/"assistant", "content": "..."}]

    Returns:
        Assistant response string

    Raises:
        ValueError: If role is unknown or API key is missing
        Exception: If API call fails
    """
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty")

    client = initialize_client()
    model = get_gemini_model()
    system_prompt = get_system_prompt(role)

    # Convert history to Gemini format
    messages = []
    for msg in history:
        messages.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}]
        })

    # Add the new user message
    messages.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    # Create chat and add system prompt as first message
    chat = client.chats.create(model=model)
    chat.system_instruction = system_prompt

    # Send message and get response
    response = chat.send_message(messages[-1]["parts"][0]["text"])

    # Handle both streaming and non-streaming responses
    if hasattr(response, 'text'):
        return response.text
    else:
        # If response is a generator/iterator, collect all chunks
        full_response = ""
        for chunk in response:
            if hasattr(chunk, 'text'):
                full_response += chunk.text
        return full_response


def get_response_stream(user_message: str, role: str, history: list[dict], model: str = None):
    """Get streaming response from Gemini API.

    Yields text chunks as they arrive from the API.

    Args:
        user_message: The user's latest message
        role: User role ("employee", "engineer", or "admin")
        history: List of previous messages
        model: Gemini model to use (defaults to config value)

    Yields:
        Text chunks from the response
    """
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty")

    # Validate role
    from src.prompts import get_available_roles
    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    client = initialize_client()
    model_name = model or get_gemini_model()
    system_prompt = get_system_prompt(role)

    # Create chat and set system instruction
    chat = client.chats.create(model=model_name)
    chat.system_instruction = system_prompt

    # Add history to chat - send only non-empty messages
    for msg in history:
        content = msg.get("content", "").strip()
        if content:
            chat.send_message(content)

    # Get streaming response for the new message
    response = chat.send_message(user_message)

    # If response is iterable (streaming), yield chunks
    try:
        yielded_any = False
        for chunk in response:
            if hasattr(chunk, 'text') and chunk.text:
                yield chunk.text
                yielded_any = True
        if not yielded_any:
            # Response object exists but no text chunks; try direct access
            if hasattr(response, 'text') and response.text:
                yield response.text
    except TypeError:
        # If not iterable, yield the full response
        if hasattr(response, 'text'):
            yield response.text
