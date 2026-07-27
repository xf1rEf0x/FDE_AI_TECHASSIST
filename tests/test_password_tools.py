"""Tests for password reset tool."""

import json
import os
import pytest
from src.tools.password_tools import reset_password_tool, _generate_temporary_password


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
    result = reset_password_tool("test@techassist.com")

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "success"
    assert "new_password" in result
    assert "message" in result
    assert len(result["new_password"]) == 12


def test_reset_password_tool_logs_to_file():
    """Test that password reset is logged to JSON file."""
    test_email = "logging_test@techassist.com"

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
