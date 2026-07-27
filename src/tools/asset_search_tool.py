"""LangChain tool for searching employee assets."""

import json
import os
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool


ASSETS_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "employee_assets.json"


def load_assets_data() -> dict:
    """Load employee assets data from JSON file.

    Returns:
        Dictionary containing employee assets data

    Raises:
        FileNotFoundError: If assets file not found
        json.JSONDecodeError: If JSON is invalid
    """
    if not ASSETS_DATA_PATH.exists():
        raise FileNotFoundError(f"Assets data file not found: {ASSETS_DATA_PATH}")

    with open(ASSETS_DATA_PATH, "r") as f:
        return json.load(f)


def search_assets_by_employee(employee_name: str, asset_type: Optional[str] = None, user_id: str = None, is_admin: bool = False) -> list[dict]:
    """Search assets by employee name and optionally filter by asset type.

    Args:
        employee_name: Full name or partial name of employee
        asset_type: Optional asset type filter (e.g., "Laptop", "Monitor", "Software License")
        user_id: Optional current user's employee ID for access control
        is_admin: Whether current user is admin (bypasses user_id filter)

    Returns:
        List of matching assets with employee info
    """
    data = load_assets_data()
    results = []

    employee_name_lower = employee_name.lower()
    asset_type_lower = asset_type.lower() if asset_type else None

    # Filter employees by user access level
    employees = data.get("employees", [])
    if not is_admin and user_id:
        employees = [emp for emp in employees if emp.get("employee_id") == user_id]

    for employee in employees:
        if employee_name_lower in employee["name"].lower():
            for asset in employee.get("assets", []):
                if asset_type_lower and asset_type_lower not in asset.get("type", "").lower():
                    continue

                results.append({
                    "employee_id": employee["employee_id"],
                    "employee_name": employee["name"],
                    "department": employee["department"],
                    "email": employee["email"],
                    **asset
                })

    return results


def search_assets_by_serial(serial_number: str, user_id: str = None, is_admin: bool = False) -> list[dict]:
    """Search assets by serial number or license key.

    Args:
        serial_number: Serial number, license key, or partial match
        user_id: Optional current user's employee ID for access control
        is_admin: Whether current user is admin (bypasses user_id filter)

    Returns:
        List of matching assets
    """
    data = load_assets_data()
    results = []

    serial_lower = serial_number.lower()

    # Filter employees by user access level
    employees = data.get("employees", [])
    if not is_admin and user_id:
        employees = [emp for emp in employees if emp.get("employee_id") == user_id]

    for employee in employees:
        for asset in employee.get("assets", []):
            serial = asset.get("serial_number", "").lower()
            license_key = asset.get("license_key", "").lower()

            if serial_lower in serial or serial_lower in license_key:
                results.append({
                    "employee_id": employee["employee_id"],
                    "employee_name": employee["name"],
                    "department": employee["department"],
                    "email": employee["email"],
                    **asset
                })

    return results


def search_assets_by_type(asset_type: str, user_id: str = None, is_admin: bool = False) -> list[dict]:
    """Search assets by type across all employees.

    Args:
        asset_type: Type of asset (e.g., "Laptop", "Monitor", "Software License", "Printer")
        user_id: Optional current user's employee ID for access control
        is_admin: Whether current user is admin (bypasses user_id filter)

    Returns:
        List of matching assets
    """
    data = load_assets_data()
    results = []

    asset_type_lower = asset_type.lower()

    # Filter employees by user access level
    employees = data.get("employees", [])
    if not is_admin and user_id:
        employees = [emp for emp in employees if emp.get("employee_id") == user_id]

    for employee in employees:
        for asset in employee.get("assets", []):
            if asset_type_lower in asset.get("type", "").lower():
                results.append({
                    "employee_id": employee["employee_id"],
                    "employee_name": employee["name"],
                    "department": employee["department"],
                    "email": employee["email"],
                    **asset
                })

    return results


@tool
def search_employee_assets(query: str, asset_type: Optional[str] = None, user_id: str = None, is_admin: bool = False) -> str:
    """Search for employee assets by name, serial number, or type.

    This tool searches across all employee assets in the system. You can:
    - Search by employee name (e.g., "Alice Johnson")
    - Search by serial number or license key (e.g., "C02XQ8NWLXJX")
    - Filter by asset type (e.g., "Laptop", "Monitor", "Software License", "Printer")

    Args:
        query: Search query (employee name or serial number)
        asset_type: Optional asset type to filter by
        user_id: Optional current user's employee ID for access control
        is_admin: Whether current user is admin (bypasses user_id filter)

    Returns:
        Formatted string with search results
    """
    results = []

    # Try searching by employee name first
    results.extend(search_assets_by_employee(query, asset_type, user_id=user_id, is_admin=is_admin))

    # If no results, try searching by serial number
    if not results:
        results.extend(search_assets_by_serial(query, user_id=user_id, is_admin=is_admin))

    # If still no results, try searching by type only (if asset_type provided)
    if not results and asset_type:
        results.extend(search_assets_by_type(asset_type, user_id=user_id, is_admin=is_admin))

    if not results:
        return f"No assets found matching query: '{query}' {f'with type: {asset_type}' if asset_type else ''}"

    # Format results for display
    formatted_results = []
    seen_employees = set()

    for asset in results:
        emp_key = asset["employee_id"]

        # Add employee header once per employee
        if emp_key not in seen_employees:
            formatted_results.append(f"\n**Employee:** {asset['employee_name']} ({asset['employee_id']})")
            formatted_results.append(f"**Department:** {asset['department']}")
            formatted_results.append(f"**Email:** {asset['email']}")
            formatted_results.append("---")
            seen_employees.add(emp_key)

        # Add asset details
        asset_type = asset.get("type", "Unknown")
        formatted_results.append(f"\n**Asset Type:** {asset_type}")
        formatted_results.append(f"**Asset ID:** {asset['asset_id']}")

        # Type-specific details
        if asset_type == "Laptop":
            formatted_results.append(f"**Model:** {asset.get('model')}")
            formatted_results.append(f"**Serial Number:** {asset.get('serial_number')}")
            formatted_results.append(f"**OS:** {asset.get('os')}")
        elif asset_type == "Monitor":
            formatted_results.append(f"**Model:** {asset.get('model')}")
            formatted_results.append(f"**Serial Number:** {asset.get('serial_number')}")
            formatted_results.append(f"**Size/Resolution:** {asset.get('size')} @ {asset.get('resolution')}")
        elif asset_type == "Printer":
            formatted_results.append(f"**Model:** {asset.get('model')}")
            formatted_results.append(f"**Serial Number:** {asset.get('serial_number')}")
            formatted_results.append(f"**Network Address:** {asset.get('network_address')}")
        elif asset_type == "Software License":
            formatted_results.append(f"**Software:** {asset.get('name')}")
            formatted_results.append(f"**License Key:** {asset.get('license_key')}")
            formatted_results.append(f"**License Type:** {asset.get('license_type')}")

        formatted_results.append(f"**Purchase Date:** {asset.get('purchase_date')}")
        formatted_results.append(f"**Warranty/Expiry:** {asset.get('warranty_end') or asset.get('expiry_date')}")
        formatted_results.append(f"**Status:** {asset.get('status')}")

    return "\n".join(formatted_results)
