"""Ticket creation and status checking tools for agents."""

from src.storage.ticket_store import TicketStore

# Module-level ticket store instance (shared across all tool calls)
ticket_store = TicketStore("data/tickets.json")


def create_ticket_tool(user_email: str, title: str, description: str) -> dict:
    """
    Create a new support ticket for the user.

    Args:
        user_email: Email of the user creating the ticket
        title: Title of the ticket
        description: Detailed description of the issue

    Returns:
        dict with keys:
            - status: "success"
            - ticket_id: ID of the created ticket
            - message: Human-readable confirmation message
    """
    ticket = ticket_store.create_ticket(user_email, title, description)
    return {
        "status": "success",
        "ticket_id": ticket.id,
        "message": f"Ticket {ticket.id} created successfully.",
    }


def check_ticket_status_tool(user_email: str, ticket_id: str) -> dict:
    """
    Check the status of a ticket (owner only).

    Args:
        user_email: Email of the user requesting the status
        ticket_id: ID of the ticket to check

    Returns:
        dict with keys:
            - status: "success" or "error"
            - ticket: (if success) dict with ticket_id, title, description, status, created_at
            - message: (if error) error message
    """
    ticket = ticket_store.get_ticket(ticket_id, user_email)
    if ticket is None:
        return {
            "status": "error",
            "message": "Ticket not found or access denied.",
        }

    return {
        "status": "success",
        "ticket": {
            "ticket_id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status,
            "created_at": ticket.created_at,
        },
    }


def list_tickets_tool(user_email: str) -> dict:
    """
    List all tickets for the user.

    Args:
        user_email: Email of the user whose tickets to list

    Returns:
        dict with keys:
            - status: "success"
            - tickets: list of dicts with ticket_id, title, status, created_at
    """
    tickets = ticket_store.list_user_tickets(user_email)
    return {
        "status": "success",
        "tickets": [
            {
                "ticket_id": t.id,
                "title": t.title,
                "status": t.status,
                "created_at": t.created_at,
            }
            for t in tickets
        ],
    }
