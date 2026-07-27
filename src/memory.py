"""Memory adapters to convert between Streamlit session state and LangChain memory."""

from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


def history_to_langchain_memory(history: list[dict]) -> ConversationBufferMemory:
    """Convert Streamlit conversation history to LangChain ConversationBufferMemory.

    Args:
        history: List of messages in format [{"role": "user"/"assistant", "content": "..."}]

    Returns:
        ConversationBufferMemory populated with history
    """
    memory = ConversationBufferMemory(human_prefix="User", ai_prefix="Assistant")

    for msg in history:
        if msg["role"] == "user":
            memory.save_context({"input": msg["content"]}, {"output": ""})
        elif msg["role"] == "assistant":
            # For assistant messages, we need to pair them with the preceding user input
            # This is a simplified approach: we assume messages alternate
            pass

    return memory


def extract_history_from_memory(memory: ConversationBufferMemory) -> list[dict]:
    """Extract conversation history from LangChain memory back to Streamlit format.

    Args:
        memory: ConversationBufferMemory instance

    Returns:
        List of messages in format [{"role": "user"/"assistant", "content": "..."}]
    """
    history = []
    buffer = memory.buffer

    # Parse the buffer string (format: "User: ...\nAssistant: ...\n")
    lines = buffer.split("\n")
    current_role = None
    current_content = []

    for line in lines:
        if line.startswith("User:"):
            if current_role and current_content:
                history.append({"role": current_role, "content": " ".join(current_content)})
            current_role = "user"
            current_content = [line[5:].strip()]
        elif line.startswith("Assistant:"):
            if current_role and current_content:
                history.append({"role": current_role, "content": " ".join(current_content)})
            current_role = "assistant"
            current_content = [line[10:].strip()]
        elif line.strip() and current_role:
            current_content.append(line.strip())

    # Don't forget the last message
    if current_role and current_content:
        history.append({"role": current_role, "content": " ".join(current_content)})

    return history
