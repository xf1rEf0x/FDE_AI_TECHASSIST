"""Entry point for `langgraph dev` / LangGraph Studio.

Studio needs a module-level compiled graph it can import with no arguments.
`SupervisorAgent.graph` only exists per-instance (built from a real user's
email/role in `__init__`), so this builds one placeholder instance purely
for visualization/debugging and exports its graph.
"""

from src.agents.supervisor_agent import SupervisorAgent

_supervisor = SupervisorAgent(user_email="studio@techassist.com", user_role="admin")
graph = _supervisor.graph
