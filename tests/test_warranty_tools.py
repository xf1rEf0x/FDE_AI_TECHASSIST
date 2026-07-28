"""Tests for asset warranty/license check tool."""

from datetime import date
from src.tools.warranty_tools import check_asset_warranty, _warranty_status
from src.tools.asset_search_tool import search_assets_by_employee


class TestCheckAssetWarranty:
    def test_reports_status_for_each_asset(self):
        """Warranty check reports ACTIVE or EXPIRED per asset, matching the raw data,
        with each asset's status paired to its own line (not just present anywhere
        in the blob, which would let a "same status for every asset" bug pass)."""
        result = check_asset_warranty.invoke({"query": "Alice Johnson"})
        assets = search_assets_by_employee("Alice Johnson")
        assert assets, "fixture data must contain Alice's assets"

        result_lines = result.splitlines()
        for asset in assets:
            expiry = asset.get("warranty_end") or asset.get("expiry_date")
            try:
                expected_status = (
                    "ACTIVE" if date.fromisoformat(expiry) >= date.today() else "EXPIRED"
                )
            except (TypeError, ValueError):
                expected_status = "UNKNOWN"

            asset_line = next(
                (line for line in result_lines if asset["asset_id"] in line), None
            )
            assert asset_line is not None, f"no result line for {asset['asset_id']}"
            assert expected_status in asset_line

    def test_search_by_serial_number(self):
        """Warranty check also matches by serial number."""
        result = check_asset_warranty.invoke({"query": "C02XQ8NWLXJX"})
        assert "LAP-2024-001" in result

    def test_no_match_returns_message(self):
        """Unknown query returns a clear no-match message, not an error."""
        result = check_asset_warranty.invoke({"query": "NoSuchEmployee999"})
        assert "No asset found" in result

    def test_scoped_to_user_id_when_not_admin(self):
        """Non-admin user_id scoping hides other employees' assets: querying another
        employee's real name while scoped to someone else must never leak that other
        employee's assets. (Per the own-assets fallback below, this now returns the
        scoped user's own assets rather than an empty "No asset found" — mirroring
        search_employee_assets — but Bob's asset IDs must still never appear.)"""
        result = check_asset_warranty.invoke({"query": "Bob Smith", "user_id": "EMP001", "is_admin": False})
        assert "LAP-2024-002" not in result  # Bob's laptop must not leak
        assert "Bob Smith" not in result

    def test_missing_expiry_is_unknown(self):
        """An asset with no expiry date on file reports UNKNOWN, not EXPIRED."""
        assert _warranty_status(None) == "UNKNOWN"
        assert _warranty_status("") == "UNKNOWN"

    def test_malformed_expiry_is_unknown_not_a_crash(self):
        """A malformed/non-ISO date string reports UNKNOWN instead of raising."""
        assert _warranty_status("not-a-date") == "UNKNOWN"
        assert _warranty_status("2024-13-45") == "UNKNOWN"

    def test_falls_back_to_own_assets_when_query_matches_neither_name_nor_serial(self):
        """A non-admin querying by their own email (not name/serial) should still get
        their real assets back, matching search_employee_assets's fallback behavior,
        instead of a contradictory 'No asset found'."""
        result = check_asset_warranty.invoke(
            {"query": "alice.johnson@techassist.com", "user_id": "EMP001", "is_admin": False}
        )
        assert "No asset found" not in result
        assert "LAP-2024-001" in result
