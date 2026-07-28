"""LangChain tool for checking employee asset warranty/license status."""

from datetime import date
from langchain_core.tools import tool

from src.tools.asset_search_tool import search_assets_by_employee, search_assets_by_serial


def _is_active(expiry: str | None) -> bool:
    """Return True if the given ISO date string is today or later."""
    if not expiry:
        return False
    return date.fromisoformat(expiry) >= date.today()


@tool
def check_asset_warranty(query: str, user_id: str = None, is_admin: bool = False) -> str:
    """Check whether an employee's asset warranty or software license is still active.

    Args:
        query: Employee name or serial/license key to look up.
        user_id: Optional current user's employee ID for access control.
        is_admin: Whether the current user is admin (bypasses user_id filter).

    Returns:
        Formatted string reporting ACTIVE/EXPIRED status per matching asset.
    """
    results = search_assets_by_employee(query, user_id=user_id, is_admin=is_admin)
    if not results:
        results = search_assets_by_serial(query, user_id=user_id, is_admin=is_admin)

    if not results:
        return f"No asset found matching '{query}'."

    lines = []
    for asset in results:
        expiry = asset.get("warranty_end") or asset.get("expiry_date")
        status = "ACTIVE" if _is_active(expiry) else "EXPIRED"
        label = asset.get("model") or asset.get("name") or asset.get("asset_id")
        expiry_note = f"expires {expiry}" if expiry else "no expiry date on file"
        lines.append(f"{asset['asset_id']} ({label}): warranty/license {status} ({expiry_note})")

    return "\n".join(lines)
