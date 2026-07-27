"""Software request tools for the SoftwareRequestAgent."""

from src.storage.software_request_store import SoftwareRequestStore

# Module-level store instance (shared across all tool calls)
software_store = SoftwareRequestStore("data/software_requests.json")


def create_software_request_tool(
    requester_email: str, software_name: str, version: str, justification: str
) -> dict:
    """
    Create a new software request for the user.

    Args:
        requester_email: Email of the user requesting software
        software_name: Name of the software (e.g., "VSCode")
        version: Version or "latest"
        justification: Why the software is needed

    Returns:
        dict with keys: status, request_id, message
    """
    request = software_store.create_request(requester_email, software_name, version, justification)
    return {
        "status": "success",
        "request_id": request.id,
        "message": f"Software request created successfully. Request ID: {request.id}. Status: pending approval.",
    }


def check_request_status_tool(requester_email: str, request_id: str) -> dict:
    """
    Check the status of a software request (owner only).

    Args:
        requester_email: Email of the user checking the request
        request_id: ID of the request to check

    Returns:
        dict with keys: status, request (if success), message (if error)
    """
    request = software_store.get_request(request_id, requester_email)
    if request is None:
        return {
            "status": "error",
            "message": "Request not found or access denied.",
        }

    return {
        "status": "success",
        "request": {
            "request_id": request.id,
            "software_name": request.software_name,
            "version": request.version,
            "justification": request.justification,
            "status": request.status,
            "request_date": request.request_date,
            "approved_by": request.approved_by,
            "approved_date": request.approved_date,
            "rejection_reason": request.rejection_reason,
        },
    }


def list_my_requests_tool(requester_email: str) -> dict:
    """
    List all software requests for the user.

    Args:
        requester_email: Email of the user

    Returns:
        dict with keys: status, requests (list of dicts)
    """
    requests = software_store.list_user_requests(requester_email)
    return {
        "status": "success",
        "requests": [
            {
                "request_id": r.id,
                "software_name": r.software_name,
                "version": r.version,
                "status": r.status,
                "request_date": r.request_date,
                "approved_by": r.approved_by,
            }
            for r in requests
        ],
    }


def list_pending_requests_tool() -> dict:
    """
    List all pending software requests (admin tool).

    Returns:
        dict with keys: status, requests
    """
    requests = software_store.list_pending_requests()
    return {
        "status": "success",
        "requests": [
            {
                "request_id": r.id,
                "requester_email": r.requester_email,
                "software_name": r.software_name,
                "version": r.version,
                "justification": r.justification,
                "request_date": r.request_date,
            }
            for r in requests
        ],
    }


def approve_request_tool(
    request_id: str, approver_email: str, approved_by_name: str
) -> dict:
    """
    Approve a pending software request (admin only).

    Args:
        request_id: ID of the request to approve
        approver_email: Email of the admin approving
        approved_by_name: Name of the approver (for record)

    Returns:
        dict with keys: status, request, message
    """
    request = software_store.approve_request(request_id, approver_email, approved_by_name)
    if request is None:
        return {
            "status": "error",
            "message": "Request not found or cannot be approved (already approved/rejected).",
        }

    return {
        "status": "success",
        "request": {
            "request_id": request.id,
            "software_name": request.software_name,
            "status": request.status,
            "approved_by": request.approved_by,
            "approved_date": request.approved_date,
        },
        "message": f"Request {request_id} approved successfully.",
    }


def reject_request_tool(request_id: str, approver_email: str, reason: str) -> dict:
    """
    Reject a pending software request (admin only).

    Args:
        request_id: ID of the request to reject
        approver_email: Email of the admin rejecting
        reason: Reason for rejection

    Returns:
        dict with keys: status, message
    """
    request = software_store.reject_request(request_id, approver_email, reason)
    if request is None:
        return {
            "status": "error",
            "message": "Request not found or cannot be rejected (already approved/rejected).",
        }

    return {
        "status": "success",
        "message": f"Request {request_id} rejected. Reason: {reason}",
    }
