"""Tests for asset warranty/license check tool."""

from datetime import date
from src.tools.warranty_tools import check_asset_warranty
from src.tools.asset_search_tool import search_assets_by_employee


class TestCheckAssetWarranty:
    def test_reports_status_for_each_asset(self):
        """Warranty check reports ACTIVE or EXPIRED per asset, matching the raw data."""
        result = check_asset_warranty.invoke({"query": "Alice Johnson"})
        assets = search_assets_by_employee("Alice Johnson")
        assert assets, "fixture data must contain Alice's assets"

        for asset in assets:
            expiry = asset.get("warranty_end") or asset.get("expiry_date")
            expected_status = "ACTIVE" if date.fromisoformat(expiry) >= date.today() else "EXPIRED"
            assert asset["asset_id"] in result
            assert expected_status in result

    def test_search_by_serial_number(self):
        """Warranty check also matches by serial number."""
        result = check_asset_warranty.invoke({"query": "C02XQ8NWLXJX"})
        assert "LAP-2024-001" in result

    def test_no_match_returns_message(self):
        """Unknown query returns a clear no-match message, not an error."""
        result = check_asset_warranty.invoke({"query": "NoSuchEmployee999"})
        assert "No asset found" in result

    def test_scoped_to_user_id_when_not_admin(self):
        """Non-admin user_id scoping hides other employees' assets."""
        result = check_asset_warranty.invoke({"query": "Bob Smith", "user_id": "EMP001", "is_admin": False})
        assert "No asset found" in result
