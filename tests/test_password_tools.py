"""Tests for password reset tool."""

import json
import os
import pytest
from src.tools.password_tools import reset_password_tool, _generate_temporary_password
from src.auth_config import USERS


def test_generate_temporary_password():
    """Test that generated password is 12 chars and alphanumeric."""
    password = _generate_temporary_password()
    assert len(password) == 12
    assert password.isalnum()
    assert password.replace(password[0], "") != password  # Not all same char


def test_generate_temporary_password_uniqueness():
    """Test that generated passwords are unique (high probability)."""
    passwords = [_generate_temporary_password() for _ in range(100)]
    assert len(set(passwords)) > 95  # At least 95 unique out of 100


def test_reset_password_tool_returns_valid_response():
    """Test that reset_password_tool returns expected response structure."""
    result = reset_password_tool("alice@techassist.com")

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "success"
    assert "new_password" in result
    assert "message" in result
    assert len(result["new_password"]) == 12


def test_reset_password_tool_updates_user_password():
    """Test that password reset actually updates the user's password in USERS."""
    test_email = "bob@techassist.com"
    old_password = USERS[test_email]["password"]

    result = reset_password_tool(test_email)

    assert result["status"] == "success"
    assert USERS[test_email]["password"] == result["new_password"]
    assert USERS[test_email]["password"] != old_password


def test_reset_password_tool_fails_for_nonexistent_user():
    """Test that resetting password for nonexistent user returns error."""
    result = reset_password_tool("nonexistent@techassist.com")

    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_reset_password_tool_logs_to_file():
    """Test that password reset is logged to JSON file."""
    test_email = "carol@techassist.com"

    # Ensure file doesn't exist first
    if os.path.exists("data/passwords.json"):
        os.remove("data/passwords.json")

    result = reset_password_tool(test_email)

    # Check file was created and contains the reset
    assert os.path.exists("data/passwords.json")
    with open("data/passwords.json", "r") as f:
        log = json.load(f)

    assert "resets" in log
    assert len(log["resets"]) > 0
    last_reset = log["resets"][-1]
    assert last_reset["user_email"] == test_email
    assert last_reset["password"] == result["new_password"]

    # Cleanup
    if os.path.exists("data/passwords.json"):
        os.remove("data/passwords.json")
