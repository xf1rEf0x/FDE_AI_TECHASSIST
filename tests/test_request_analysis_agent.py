# tests/test_request_analysis_agent.py
"""Tests for the Request Analysis Agent (structured-output extraction)."""

from unittest.mock import MagicMock
from src.agents.request_analysis_agent import analyze_request, RequestAnalysis


def test_analyze_request_returns_structured_output():
    expected = RequestAnalysis(issue="VPN Connection", device="Company Laptop", action="Create Ticket")
    structured_llm = MagicMock()
    structured_llm.invoke.return_value = expected
    llm = MagicMock()
    llm.with_structured_output.return_value = structured_llm

    result = analyze_request(llm, "My laptop isn't connecting to the company VPN, create a ticket.")

    llm.with_structured_output.assert_called_once_with(RequestAnalysis)
    assert structured_llm.invoke.call_count == 1
    assert result == expected


def test_request_analysis_model_requires_all_fields():
    analysis = RequestAnalysis(issue="Password Reset", device="Unknown", action="Reset Password")
    assert analysis.issue == "Password Reset"
    assert analysis.device == "Unknown"
    assert analysis.action == "Reset Password"
