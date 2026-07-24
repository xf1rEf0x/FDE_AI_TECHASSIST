"""Unit tests for role-based prompts."""

import pytest
from src.prompts import get_system_prompt, get_available_roles, SYSTEM_PROMPTS


def test_employee_system_prompt_exists():
    """Verify employee prompt exists and is non-empty."""
    prompt = get_system_prompt("employee")
    assert prompt is not None
    assert len(prompt) > 0
    assert "employee" in prompt.lower()


def test_engineer_system_prompt_exists():
    """Verify engineer prompt exists and has technical content."""
    prompt = get_system_prompt("engineer")
    assert prompt is not None
    assert len(prompt) > 0
    assert "engineer" in prompt.lower() or "technical" in prompt.lower()


def test_admin_system_prompt_exists():
    """Verify admin prompt exists and includes policy language."""
    prompt = get_system_prompt("admin")
    assert prompt is not None
    assert len(prompt) > 0
    assert any(word in prompt.lower() for word in ["admin", "policy", "security"])


def test_prompts_differ_by_role():
    """Verify that prompts are different for each role."""
    employee_prompt = get_system_prompt("employee")
    engineer_prompt = get_system_prompt("engineer")
    admin_prompt = get_system_prompt("admin")

    assert employee_prompt != engineer_prompt
    assert engineer_prompt != admin_prompt
    assert employee_prompt != admin_prompt


def test_invalid_role_raises_error():
    """Verify that invalid role raises ValueError."""
    with pytest.raises(ValueError, match="Unknown role"):
        get_system_prompt("invalid_role")


def test_get_available_roles():
    """Verify list of available roles."""
    roles = get_available_roles()
    assert "employee" in roles
    assert "engineer" in roles
    assert "admin" in roles
    assert len(roles) == 3


def test_system_prompts_dict_complete():
    """Verify SYSTEM_PROMPTS dict has all required roles."""
    assert "employee" in SYSTEM_PROMPTS
    assert "engineer" in SYSTEM_PROMPTS
    assert "admin" in SYSTEM_PROMPTS
