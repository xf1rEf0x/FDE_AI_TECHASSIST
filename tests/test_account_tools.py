"""Tests for account unlock tool."""

import json
import shutil

import pytest
from src import auth_config
from src.auth_config import get_account_status, set_account_status
from src.tools.account_tools import unlock_account_tool


@pytest.fixture(autouse=True)
def isolated_users_file(tmp_path, monkeypatch):
    """Redirect the users JSON file to an isolated temp copy for each test."""
    tmp_file = tmp_path / "users.json"
    shutil.copy(auth_config.USERS_FILE, tmp_file)
    monkeypatch.setattr(auth_config, "USERS_FILE", tmp_file)


@pytest.fixture
def locked_user():
    """Fixture: lock carol's account for the test via the persisted store."""
    email = "carol@techassist.com"
    set_account_status(email, "locked")
    return email


def test_unlock_account_tool_unlocks_locked_account(locked_user):
    """Test that unlocking a locked account sets status to unlocked."""
    result = unlock_account_tool(locked_user)

    assert result["status"] == "success"
    assert get_account_status(locked_user) == "unlocked"


def test_unlock_account_tool_persists_across_reload(locked_user):
    """Test that the unlock is written to disk (simulates app restart)."""
    unlock_account_tool(locked_user)

    with open(auth_config.USERS_FILE) as f:
        users = json.load(f)
    assert users[locked_user]["account_status"] == "unlocked"


def test_unlock_account_tool_fails_for_already_unlocked_account():
    """Test that unlocking an already-unlocked account returns error."""
    result = unlock_account_tool("alice@techassist.com")

    assert result["status"] == "error"
    assert "not locked" in result["message"]


def test_unlock_account_tool_fails_for_nonexistent_user():
    """Test that unlocking a nonexistent user returns error."""
    result = unlock_account_tool("nonexistent@techassist.com")

    assert result["status"] == "error"
    assert "not found" in result["message"]
