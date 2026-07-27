"""Tests for asset search tool."""

import pytest
from src.tools.asset_search_tool import (
    search_assets_by_employee,
    search_assets_by_serial,
    search_assets_by_type,
    search_employee_assets,
)


class TestAssetSearch:
    """Test asset search functionality."""

    def test_search_by_employee_name(self):
        """Test searching by employee name."""
        results = search_assets_by_employee("Alice Johnson")
        assert len(results) > 0
        assert results[0]["employee_name"] == "Alice Johnson"

    def test_search_by_partial_employee_name(self):
        """Test searching by partial employee name."""
        results = search_assets_by_employee("Bob")
        assert len(results) > 0
        assert "Bob" in results[0]["employee_name"]

    def test_search_by_asset_type_filter(self):
        """Test filtering by asset type."""
        results = search_assets_by_employee("Alice", asset_type="Laptop")
        assert len(results) == 1
        assert results[0]["type"] == "Laptop"

    def test_search_by_serial_number(self):
        """Test searching by serial number."""
        results = search_assets_by_serial("C02XQ8NWLXJX")
        assert len(results) == 1
        assert results[0]["serial_number"] == "C02XQ8NWLXJX"

    def test_search_by_license_key(self):
        """Test searching by license key."""
        results = search_assets_by_serial("IJLU-123456-ABCDEF")
        assert len(results) == 1
        assert results[0]["license_key"] == "IJLU-123456-ABCDEF"

    def test_search_by_asset_type(self):
        """Test searching by asset type across all employees."""
        results = search_assets_by_type("Laptop")
        assert len(results) == 4  # 4 employees in mock data, each with a laptop
        assert all(asset["type"] == "Laptop" for asset in results)

    def test_search_returns_empty_for_no_match(self):
        """Test searching for non-existent asset."""
        results = search_assets_by_employee("NonExistentEmployee")
        assert len(results) == 0

    def test_search_employee_assets_tool_by_name(self):
        """Test the main search tool with employee name."""
        result = search_employee_assets.invoke({"query": "Alice", "asset_type": None})
        assert isinstance(result, str)
        assert "Alice Johnson" in result
        assert "Laptop" in result

    def test_search_employee_assets_tool_by_serial(self):
        """Test the main search tool with serial number."""
        result = search_employee_assets.invoke({"query": "C02XQ8NWLXJX", "asset_type": None})
        assert isinstance(result, str)
        assert "Alice Johnson" in result

    def test_search_employee_assets_tool_with_type_filter(self):
        """Test the main search tool with asset type filter."""
        result = search_employee_assets.invoke({"query": "David", "asset_type": "Monitor"})
        assert isinstance(result, str)
        assert "Monitor" in result
        assert "David Wilson" in result

    def test_search_employee_assets_tool_no_results(self):
        """Test the main search tool when no results found."""
        result = search_employee_assets.invoke({"query": "XYZ999", "asset_type": None})
        assert isinstance(result, str)
        assert "No assets found" in result

    def test_search_employee_assets_tool_falls_back_to_own_scope(self):
        """Test that a non-admin's own-scope search still returns their
        assets even when the query (e.g. their email) matches neither name,
        serial, nor a given asset type."""
        result = search_employee_assets.invoke(
            {"query": "alice@techassist.com", "asset_type": None, "user_id": "EMP001", "is_admin": False}
        )
        assert isinstance(result, str)
        assert "Alice Johnson" in result
        assert "Laptop" in result

    def test_search_employee_assets_tool_accepts_none_user_id(self):
        """Test that an admin (whose employee_id is None) doesn't crash the tool."""
        result = search_employee_assets.invoke(
            {"query": "nonexistent-query", "asset_type": None, "user_id": None, "is_admin": True}
        )
        assert isinstance(result, str)
        assert "No assets found" in result
