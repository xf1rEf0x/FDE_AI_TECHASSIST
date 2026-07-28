"""Tool for saving a support interaction summary (used by the Notification Agent)."""

from src.storage.summary_store import SummaryStore

# Module-level store instance (shared across all tool calls), same pattern as
# src/tools/ticket_tools.py's ticket_store.
summary_store = SummaryStore("data/support_summaries.json")


def generate_summary_tool(user_email: str, summary: str, ticket_id: str = None) -> dict:
    """
    Save a support interaction summary.

    Args:
        user_email: Email of the user the summary is for.
        summary: Human-readable summary text.
        ticket_id: Optional related ticket ID.

    Returns:
        dict with keys:
            - status: "success"
            - summary_id: ID of the saved summary
            - message: Human-readable confirmation message
    """
    record = summary_store.save_summary(user_email, summary, ticket_id)
    return {
        "status": "success",
        "summary_id": record.id,
        "message": f"Summary {record.id} saved.",
    }
