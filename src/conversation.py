"""Conversation handler using LangChain with HuggingFace models."""

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from src.langchain_integration import create_langchain_model
from src.prompts import get_system_prompt, get_available_roles


def get_response(user_message: str, role: str, history: list[dict], temperature: float = 0.7, provider: str = "huggingface") -> str:
    """Get response from LLM via LangChain.

    Args:
        user_message: The user's latest message
        role: User role ("employee", "engineer", or "admin")
        history: List of previous messages in format [{"role": "user"/"assistant", "content": "..."}]
        temperature: Temperature for response generation (0.0 - 2.0)
        provider: "huggingface" or "gemini"

    Returns:
        Assistant response string

    Raises:
        ValueError: If role is unknown or API key is missing
        Exception: If LLM call fails
    """
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty")

    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    system_prompt = get_system_prompt(role)
    model = create_langchain_model(temperature, provider)

    # Build chat prompt with system instruction
    system_msg = SystemMessagePromptTemplate.from_template(system_prompt)
    human_msg = HumanMessagePromptTemplate.from_template("{user_input}")
    chat_prompt = ChatPromptTemplate.from_messages([system_msg, human_msg])

    # Create runnable chain
    chain = chat_prompt | model

    # Invoke chain and get response
    response = chain.invoke({"user_input": user_message})
    return response.content


def get_response_stream(user_message: str, role: str, history: list[dict], temperature: float = 0.7, provider: str = "huggingface"):
    """Get streaming response from LLM via LangChain.

    Yields text chunks as they arrive from the API.

    Args:
        user_message: The user's latest message
        role: User role ("employee", "engineer", or "admin")
        history: List of previous messages (used for context, not actively consumed in this version)
        temperature: Temperature for response generation (0.0 - 2.0)
        provider: "huggingface" or "gemini"

    Yields:
        Text chunks from the response

    Raises:
        ValueError: If role is unknown
    """
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty")

    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    system_prompt = get_system_prompt(role)
    llm = create_langchain_model(temperature, provider)

    # Build chat prompt
    system_msg = SystemMessagePromptTemplate.from_template(system_prompt)
    human_msg = HumanMessagePromptTemplate.from_template("{user_input}")
    chat_prompt = ChatPromptTemplate.from_messages([system_msg, human_msg])

    # Create runnable chain
    chain = chat_prompt | llm

    # For streaming, invoke chain and yield the response
    # HuggingFace via LangChain may not support true streaming; yield the full response
    response = chain.invoke({"user_input": user_message})
    text = response.content

    # Simulate streaming by yielding the response in chunks
    chunk_size = 20
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
