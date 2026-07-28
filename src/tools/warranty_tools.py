"""LangChain tool for checking employee asset warranty/license status."""

from datetime import date
from langchain_core.tools import tool

from src.tools.asset_search_tool import (
    search_assets_by_employee,
    search_assets_by_serial,
    search_assets_by_type,
)


def _warranty_status(expiry: str | None) -> str:
    """Classify an ISO date string as ACTIVE, EXPIRED, or UNKNOWN.

    UNKNOWN covers both a missing expiry date and one that isn't a valid
    ISO date string, so a malformed value degrades gracefully instead of
    raising.
    """
    if not expiry:
        return "UNKNOWN"
    try:
        parsed = date.fromisoformat(expiry)
    except ValueError:
        return "UNKNOWN"
    return "ACTIVE" if parsed >= date.today() else "EXPIRED"


@tool
def check_asset_warranty(query: str, user_id: str = None, is_admin: bool = False) -> str:
    """Check whether an employee's asset warranty or software license is still active.

    Args:
        query: Employee name or serial/license key to look up.
        user_id: Optional current user's employee ID for access control.
        is_admin: Whether the current user is admin (bypasses user_id filter).

    Returns:
        Formatted string reporting ACTIVE/EXPIRED/UNKNOWN status per matching asset.
    """
    results = search_assets_by_employee(query, user_id=user_id, is_admin=is_admin)
    if not results:
        results = search_assets_by_serial(query, user_id=user_id, is_admin=is_admin)

    # If still no results and this is a non-admin's own scoped search (e.g. the
    # query was their email/user ID rather than their name), fall back to all
    # of their own assets — the user_id scoping already narrows this to them.
    # Mirrors search_employee_assets's fallback in asset_search_tool.py.
    if not results and user_id and not is_admin:
        results = search_assets_by_type("", user_id=user_id, is_admin=is_admin)

    if not results:
        return f"No asset found matching '{query}'."

    lines = []
    for asset in results:
        expiry = asset.get("warranty_end") or asset.get("expiry_date")
        status = _warranty_status(expiry)
        label = asset.get("model") or asset.get("name") or asset.get("asset_id")
        if status != "UNKNOWN":
            expiry_note = f"expires {expiry}"
        elif expiry:
            expiry_note = f"invalid expiry date on file: {expiry}"
        else:
            expiry_note = "no expiry date on file"
        lines.append(f"{asset['asset_id']} ({label}): warranty/license {status} ({expiry_note})")

    return "\n".join(lines)
