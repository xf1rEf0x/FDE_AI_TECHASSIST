# src/agents/request_analysis_agent.py
"""Request Analysis Agent: extracts issue/device/action from free-form text via structured output."""

from pydantic import BaseModel, Field


class RequestAnalysis(BaseModel):
    """Structured extraction of an IT support request."""

    issue: str = Field(description="The type of issue, e.g. 'VPN Connection', 'Password Reset'")
    device: str = Field(description="The device involved, e.g. 'Company Laptop'. Use 'Unknown' if not mentioned.")
    action: str = Field(description="The action required, e.g. 'Create Ticket', 'Check Warranty'")


def analyze_request(llm, user_message: str) -> RequestAnalysis:
    """Run the Request Analysis Agent: a single structured-output LLM call."""
    structured_llm = llm.with_structured_output(RequestAnalysis)
    return structured_llm.invoke(
        "Extract the issue type, device, and required action from this IT support "
        f"request. Request: {user_message}"
    )
