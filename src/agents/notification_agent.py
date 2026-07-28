"""Notification Agent: presents ticket details, asks for confirmation, and saves summaries."""

from langchain_core.tools import tool

from src.agents.agent_loop import run_tool_calling_loop
from src.tools.summary_tools import generate_summary_tool

NOTIFICATION_SYSTEM_PROMPT = """You are the Notification Agent, part of TechAssist AI's \
support workflow. You are given an instruction and context describing what happened so far.

- If the instruction asks you to preview ticket details and ask for confirmation, write a \
clear preview (issue, device, warranty status, proposed ticket) and end with a question \
asking the user to confirm. Do NOT call generate_summary in this case.
- If the instruction says the user confirmed and/or the ticket has been created, call \
generate_summary(summary, ticket_id) with a concise summary of the interaction, then tell \
the user it has been saved.
"""


def _build_tools(user_email: str) -> list:
    @tool
    def generate_summary(summary: str, ticket_id: str = None) -> str:
        """Save a summary of this support interaction. Only call after the ticket has been created and the user confirmed."""
        result = generate_summary_tool(user_email, summary, ticket_id)
        return result["message"]

    return [generate_summary]


def run_notification_agent(llm, user_email: str, instruction: str, context: str = "") -> str:
    """Run the Notification Agent for one delegated task."""
    tools = _build_tools(user_email)
    messages = [("user", f"Instruction: {instruction}\n\nContext:\n{context}")]
    result = run_tool_calling_loop(llm, tools, NOTIFICATION_SYSTEM_PROMPT, messages)
    return result["text"]
