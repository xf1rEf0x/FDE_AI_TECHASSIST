"""Tests for login-to-chatbot role binding integration."""

import shutil

import pytest
from src import auth_config
from src.auth import login, is_account_locked
from src.auth_config import set_account_status
from src.tools.asset_search_tool import search_assets_by_employee


@pytest.fixture(autouse=True)
def isolated_users_file(tmp_path, monkeypatch):
    """Redirect the users JSON file to an isolated temp copy so tests don't
    depend on (or pollute) real persisted lock/unlock state."""
    tmp_file = tmp_path / "users.json"
    shutil.copy(auth_config.USERS_FILE, tmp_file)
    monkeypatch.setattr(auth_config, "USERS_FILE", tmp_file)


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

    def test_locked_account_cannot_login(self):
        """Test that a locked account cannot log in even with correct credentials."""
        set_account_status("david@techassist.com", "locked")
        assert is_account_locked("david@techassist.com")
        user = login("david@techassist.com", "password123")
        assert user is None

    def test_unlocked_account_reports_not_locked(self):
        """Test that is_account_locked returns False for unlocked accounts."""
        assert is_account_locked("alice@techassist.com") is False

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
