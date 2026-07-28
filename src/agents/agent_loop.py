# src/agents/agent_loop.py
"""Shared multi-round tool-calling loop used by the Supervisor and its sub-agents."""

from langchain_core.messages import SystemMessage, ToolMessage


def extract_text(response) -> str:
    """Extract text from an LLM response (handles both string and list content)."""
    if not hasattr(response, "content"):
        return str(response)

    content = response.content
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "".join(parts)

    return str(content)


def _extract_usage(response) -> dict | None:
    """Pull token usage out of an LLM response, if the provider reports it."""
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return None
    return {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
    }


def _sum_usage(usages: list) -> dict | None:
    """Sum token usage across one or more LLM calls."""
    usages = [u for u in usages if u]
    if not usages:
        return None
    return {
        key: sum(u[key] for u in usages)
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }


def run_tool_calling_loop(
    llm, tools: list, system_prompt: str, messages: list, max_iterations: int = 5
) -> dict:
    """Run a bind_tools loop until the model stops calling tools or max_iterations is hit.

    Args:
        llm: A LangChain chat model (not yet bound to tools).
        tools: List of @tool-decorated callables.
        system_prompt: System prompt text, prepended as a SystemMessage.
        messages: List of (role, content) tuples or BaseMessage instances forming the
            conversation so far. The latest user turn must already be included.
        max_iterations: Maximum number of tool-calling rounds before giving up.

    Returns:
        dict with keys:
            - text: final response text
            - tool_calls: list of {"name": str, "args": dict} in call order
            - token_usage: summed {"input_tokens", "output_tokens", "total_tokens"} or None
    """
    llm_with_tools = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}
    convo = [SystemMessage(system_prompt)] + list(messages)
    tool_calls_made = []
    usages = []

    response = None
    for _ in range(max_iterations):
        response = llm_with_tools.invoke(convo)
        convo.append(response)
        usages.append(_extract_usage(response))

        if not getattr(response, "tool_calls", None):
            break

        for tool_call in response.tool_calls:
            tool = tools_by_name.get(tool_call["name"])
            if tool is None:
                result = f"Error: unknown tool {tool_call['name']}"
            else:
                try:
                    result = tool.invoke(tool_call["args"])
                except Exception as e:
                    result = f"Error: {e}"
            tool_calls_made.append({"name": tool_call["name"], "args": tool_call["args"]})
            convo.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    return {
        "text": extract_text(response) if response is not None else "",
        "tool_calls": tool_calls_made,
        "token_usage": _sum_usage(usages),
    }
