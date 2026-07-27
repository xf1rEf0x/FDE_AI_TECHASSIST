"""Tests for login-to-chatbot role binding integration."""

import pytest
from src.auth import login
from src.auth_config import USERS
from src.tools.asset_search_tool import search_assets_by_employee


class TestLoginRoleBinding:
    """Test that login sets user role and asset search respects user_id."""

    def test_login_alice_sets_employee_role(self):
        """Test that Alice Johnson logs in with employee role."""
        user = login("alice@techassist.com", "password123")
        assert user is not None
        assert user["role"] == "employee"
        assert user["name"] == "Alice Johnson"
        assert user["employee_id"] == "EMP001"

    def test_login_bob_sets_employee_role(self):
        """Test that Bob Smith logs in with employee role."""
        user = login("bob@techassist.com", "password123")
        assert user is not None
        assert user["role"] == "employee"
        assert user["name"] == "Bob Smith"
        assert user["employee_id"] == "EMP002"

    def test_login_admin_sets_admin_role(self):
        """Test that admin user logs in with admin role."""
        user = login("admin@techassist.com", "admin123")
        assert user is not None
        assert user["role"] == "admin"
        assert user["name"] == "Admin User"

    def test_invalid_login_returns_none(self):
        """Test that invalid credentials return None."""
        user = login("invalid@techassist.com", "wrongpassword")
        assert user is None

    def test_asset_search_respects_user_id_alice(self):
        """Test that Alice can only see her own assets when user_id is set."""
        # Alice (EMP001) with user_id restriction should only see her assets
        results = search_assets_by_employee("Alice", user_id="EMP001", is_admin=False)
        assert len(results) > 0
        assert all(asset["employee_id"] == "EMP001" for asset in results)

    def test_asset_search_respects_user_id_bob(self):
        """Test that Bob can only see his own assets when user_id is set."""
        # Bob (EMP002) with user_id restriction should only see his assets
        results = search_assets_by_employee("Bob", user_id="EMP002", is_admin=False)
        assert len(results) > 0
        assert all(asset["employee_id"] == "EMP002" for asset in results)

    def test_asset_search_admin_bypass(self):
        """Test that admin can see all assets regardless of user_id."""
        # Admin should see all employees' assets
        results = search_assets_by_employee("Alice", user_id=None, is_admin=True)
        assert len(results) > 0
        # Even though we searched for Alice, an admin search doesn't filter by user_id
        assert all(asset["employee_name"] == "Alice Johnson" for asset in results)

    def test_asset_search_employee_cannot_see_others(self):
        """Test that employee cannot see other employees' assets even if searched."""
        # Employee EMP001 searching for Bob should get no results
        results = search_assets_by_employee("Bob", user_id="EMP001", is_admin=False)
        assert len(results) == 0  # EMP001 can only see their own assets

    def test_asset_search_by_type_respects_user_id(self):
        """Test that asset type search respects user_id restriction."""
        from src.tools.asset_search_tool import search_assets_by_type

        # Alice searching for Laptops with her user_id should only see her laptop
        results = search_assets_by_type("Laptop", user_id="EMP001", is_admin=False)
        assert len(results) == 1
        assert results[0]["employee_id"] == "EMP001"
        assert results[0]["type"] == "Laptop"

    def test_asset_search_by_serial_respects_user_id(self):
        """Test that serial number search respects user_id restriction."""
        from src.tools.asset_search_tool import search_assets_by_serial

        # Alice's laptop serial number
        results = search_assets_by_serial("C02XQ8NWLXJX", user_id="EMP001", is_admin=False)
        assert len(results) == 1
        assert results[0]["employee_id"] == "EMP001"
        assert results[0]["serial_number"] == "C02XQ8NWLXJX"

        # If a non-admin user with different ID searches for that serial, should get nothing
        results = search_assets_by_serial("C02XQ8NWLXJX", user_id="EMP002", is_admin=False)
        assert len(results) == 0
