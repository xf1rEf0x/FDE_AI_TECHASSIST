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
