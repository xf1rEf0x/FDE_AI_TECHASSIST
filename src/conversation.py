"""Conversation handler using the multi-agent Supervisor."""

from src.agents.supervisor_agent import SupervisorAgent
from src.prompts import get_available_roles


def get_agent_instance(
    user_email: str,
    role: str,
    temperature: float = 0.0,
    provider: str = "google",
    employee_id: str = None,
) -> SupervisorAgent:
    """Get a SupervisorAgent instance.

    Args:
        user_email: User's email
        role: "employee", "engineer", or "admin"
        temperature: LLM temperature (0.0 - 2.0)
        provider: LLM provider, "google" or "huggingface"
        employee_id: User's employee ID, used to scope asset lookups

    Returns:
        SupervisorAgent instance with memory
    """
    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    return SupervisorAgent(user_email, role, temperature, provider=provider, employee_id=employee_id)
