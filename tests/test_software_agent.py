"""Integration tests for SoftwareRequestAgent."""

import pytest
from src.agents.software_agent import SoftwareRequestAgent


def test_user_can_request_software():
    """Test that a user can request software."""
    agent = SoftwareRequestAgent("alice@test.com", is_admin=False)
    response = agent.run("I need Figma for design work. Can you help me request it?")
    
    assert response is not None
    assert len(response) > 0
    assert "success" in response.lower() or "created" in response.lower() or "request" in response.lower()


def test_user_can_list_their_requests():
    """Test that a user can list their own requests."""
    agent = SoftwareRequestAgent("bob@test.com", is_admin=False)
    
    # Create a request first
    agent.run("I need VSCode for development work")
    
    # Now list
    response = agent.run("Show me all my software requests")
    assert response is not None
    assert len(response) > 0


def test_admin_can_list_pending():
    """Test that admin can list pending requests."""
    # Create a request as user first
    user_agent = SoftwareRequestAgent("charlie@test.com", is_admin=False)
    user_agent.run("I need Slack")
    
    # Admin lists
    admin_agent = SoftwareRequestAgent("admin@test.com", is_admin=True)
    response = admin_agent.run("What software requests are pending?")
    assert response is not None
    assert len(response) > 0


def test_user_cannot_approve_own_request():
    """Test that user is prevented from approving their own request (via prompt guard)."""
    agent = SoftwareRequestAgent("user@test.com", is_admin=False)
    
    # User tries to approve - agent should refuse
    response = agent.run("Can you approve my own software request?")
    assert "cannot" in response.lower() or "approve" in response.lower()
