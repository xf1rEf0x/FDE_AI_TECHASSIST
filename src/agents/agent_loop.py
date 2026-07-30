# src/agents/agent_loop.py
"""Shared LLM-response helpers used by the Supervisor and its sub-agents."""


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
