# tests/test_agent_loop.py
"""Tests for the shared multi-round tool-calling loop."""

from unittest.mock import MagicMock
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from src.agents.agent_loop import run_tool_calling_loop


@tool
def add_one(n: int) -> str:
    """Add one to a number."""
    return str(n + 1)


def _mock_llm(responses):
    """Build a mock LLM whose bind_tools().invoke() yields responses in order."""
    llm_with_tools = MagicMock()
    llm_with_tools.invoke.side_effect = responses
    llm = MagicMock()
    llm.bind_tools.return_value = llm_with_tools
    return llm


def test_stops_when_no_tool_calls():
    llm = _mock_llm([AIMessage(content="Hello there")])
    result = run_tool_calling_loop(llm, [add_one], "system prompt", [("user", "hi")])
    assert result["text"] == "Hello there"
    assert result["tool_calls"] == []


def test_executes_tool_call_and_feeds_result_back():
    tool_call_response = AIMessage(
        content="",
        tool_calls=[{"name": "add_one", "args": {"n": 4}, "id": "call-1"}],
    )
    final_response = AIMessage(content="The answer is 5")
    llm = _mock_llm([tool_call_response, final_response])

    result = run_tool_calling_loop(llm, [add_one], "system prompt", [("user", "add one to 4")])

    assert result["text"] == "The answer is 5"
    assert result["tool_calls"] == [{"name": "add_one", "args": {"n": 4}}]


def test_unknown_tool_name_reports_error_without_crashing():
    tool_call_response = AIMessage(
        content="",
        tool_calls=[{"name": "does_not_exist", "args": {}, "id": "call-1"}],
    )
    final_response = AIMessage(content="I couldn't do that")
    llm = _mock_llm([tool_call_response, final_response])

    result = run_tool_calling_loop(llm, [add_one], "system prompt", [("user", "go")])

    assert result["text"] == "I couldn't do that"
    assert result["tool_calls"] == [{"name": "does_not_exist", "args": {}}]


def test_stops_at_max_iterations():
    looping_response = AIMessage(
        content="",
        tool_calls=[{"name": "add_one", "args": {"n": 1}, "id": "call-x"}],
    )
    llm = _mock_llm([looping_response] * 10)

    result = run_tool_calling_loop(llm, [add_one], "system prompt", [("user", "go")], max_iterations=3)

    assert len(result["tool_calls"]) == 3
