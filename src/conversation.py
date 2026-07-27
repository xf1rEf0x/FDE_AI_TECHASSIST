"""Conversation handler using unified LangChain agent."""

from src.agents.unified_agent import TechAssistAgent
from src.prompts import get_available_roles


def get_agent_instance(user_email: str, role: str, temperature: float = 0.0) -> TechAssistAgent:
    """Get a TechAssistAgent instance.

    Args:
        user_email: User's email
        role: "employee", "engineer", or "admin"
        temperature: LLM temperature (0.0 - 2.0)

    Returns:
        TechAssistAgent instance with memory
    """
    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    return TechAssistAgent(user_email, role, temperature)


def get_response(user_input: str, role: str, history: list, temperature: float = 0.7, provider: str = "huggingface") -> str:
    """Get response from unified agent (backward compatible).

    Args:
        user_input: User message
        role: User role
        history: Message history (ignored; agent has its own memory)
        temperature: LLM temperature
        provider: Ignored (always uses Gemini)

    Returns:
        Agent response text
    """
    if not user_input or not user_input.strip():
        raise ValueError("User message cannot be empty")

    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    # Provider parameter ignored; always use Gemini
    agent = get_agent_instance("", role, temperature)
    return agent.invoke(user_input)


def get_response_stream(user_input: str, role: str, history: list, temperature: float = 0.7, provider: str = "huggingface"):
    """Get streaming response from agent (backward compatible).

    Note: Unified agent doesn't support true streaming yet; yields full response in chunks.

    Args:
        user_input: User message
        role: User role
        history: Message history (ignored)
        temperature: LLM temperature
        provider: Ignored

    Yields:
        Text chunks from agent response
    """
    if not user_input or not user_input.strip():
        raise ValueError("User message cannot be empty")

    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    agent = get_agent_instance("", role, temperature)
    response = agent.invoke(user_input)

    # Simulate streaming by yielding in chunks
    chunk_size = 20
    for i in range(0, len(response), chunk_size):
        yield response[i:i + chunk_size]
