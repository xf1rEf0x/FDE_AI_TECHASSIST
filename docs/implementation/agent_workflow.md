# Multi-Agent Workflow Reference

This document explains how `SupervisorAgent` orchestrates the Request Analysis,
Asset & Support, and Notification agents, and lists every agent and tool in
the Phase 3 multi-agent system.

## How the chain works

The Supervisor is not a separate router process — it's a single LLM with
function-calling ([supervisor_agent.py](../../src/agents/supervisor_agent.py)),
where the other agents are wired in as ordinary tools:

```
app.py -> SupervisorAgent.invoke() -> run_tool_calling_loop() (LLM <-> tools loop)
                                          |-- analyze_support_request  (= Request Analysis Agent)
                                          |-- asset_and_ticket_support (= Asset & Support Agent)
                                          `-- notify_user              (= Notification Agent)
```

`run_tool_calling_loop` ([agent_loop.py](../../src/agents/agent_loop.py)) repeatedly
asks the LLM for a response, executes any tool calls it makes, feeds the
results back in, and repeats (up to `max_iterations`) until the model returns
plain text with no further tool calls.

Each delegation tool brackets its call with a progress callback
(`self._on_progress(...)`) so the UI can show a live "`<Agent>` working..."
status, and the Supervisor collects every agent used into `last_agents_used`
for the end-of-message tooltip.

## Agents

| Agent | Implementation | What it does | When it's invoked |
|---|---|---|---|
| **Supervisor Agent** | [supervisor_agent.py](../../src/agents/supervisor_agent.py) | The main LLM with function-calling. Reads the system prompt, decides which tools/agents to call and in what order. Holds conversation memory. | Always — the entry point for every user message |
| **Request Analysis Agent** | [request_analysis_agent.py](../../src/agents/request_analysis_agent.py) | A single structured-output LLM call that extracts `{issue, device, action}` from free-form text | When the message describes a device/VPN/hardware problem — the first step before any ticket work |
| **Asset & Support Agent** | [asset_support_agent.py](../../src/agents/asset_support_agent.py) | A small tool-calling agent with its own loop. Looks up the employee's asset, checks warranty, and creates tickets | When an asset/warranty lookup is needed, or once the user has confirmed ticket creation |
| **Notification Agent** | [notification_agent.py](../../src/agents/notification_agent.py) | A small tool-calling agent. Either previews the ticket and asks for confirmation, or saves the final interaction summary | Before ticket creation (preview) and after (summary) |

## Tools

### Direct Supervisor tools

From `build_helpdesk_tools` ([unified_agent.py:44](../../src/agents/unified_agent.py)):

| Tool | Description |
|---|---|
| `create_ticket` | Create a ticket directly (no analysis/warranty step) — for simple requests |
| `check_ticket_status` | Check the status of the user's ticket |
| `list_my_tickets` | List the user's tickets |
| `close_ticket` | Close a ticket |
| `reset_password` | Raise a password reset request (after confirmation) |
| `request_software` | Request software installation (after confirmation) |
| `check_software_request_status` | Check the status of a software request |
| `list_my_software_requests` | List the user's software requests |
| `search_knowledge_base` | RAG search over internal documentation (VPN, passwords, etc.) |
| `lookup_assets` | Search assets by name/serial/type |
| `unlock_account` *(admin)* | Unlock a user account |
| `list_pending_software_requests` *(admin)* | List all pending software requests |
| `approve_software_request` / `reject_software_request` *(admin)* | Approve or reject a request |
| `list_password_reset_requests` *(admin)* | List all pending password reset requests |

### Agent-delegation tools

Also visible to the Supervisor as ordinary tools:

| Tool | Wraps | Args |
|---|---|---|
| `analyze_support_request` | Request Analysis Agent | `user_message` |
| `asset_and_ticket_support` | Asset & Support Agent | `instruction`, `context` |
| `notify_user` | Notification Agent | `instruction`, `context` |

### Sub-agent internal tools

Not visible to the Supervisor — these exist only inside a sub-agent's own
tool-calling loop:

| Tool | Belongs to | Description |
|---|---|---|
| `search_asset` | Asset & Support Agent | Search for an asset by name/serial |
| `check_warranty` | Asset & Support Agent | Returns an ACTIVE / EXPIRED / UNKNOWN verdict |
| `create_ticket` (own copy) | Asset & Support Agent | Creates a ticket, only when the instruction explicitly says the user confirmed |
| `generate_summary` | Notification Agent | Saves the final interaction summary |

## Workflow diagram

Example prompt: *"My laptop isn't connecting to the company VPN. Create a
support ticket and check if my laptop warranty is still active."*

```
                         User message
                              |
                              v
                   +----------------------+
                   |   SUPERVISOR AGENT    |<-----------------------+
                   | (reads system prompt,  |                       |
                   |  decides what to call) |                       |
                   +-----------+-----------+                       |
                              |                                     |
        +---------------------+---------------------------+        |
        |                     |                            |        |
        v                     v                            v        |
 "technical issue      "simple request"             "device/VPN/    |
  VPN/password/network" (direct ticket,               hardware issue,|
        |               password, software,            ticket +      |
        v               unlock, list tickets, ...)     warranty needed|
 search_knowledge_base        |                               |       |
        |                     v                               v       |
   +----+----+          create_ticket /              analyze_support_request
   |resolved?|          reset_password /                     |       |
   +----+----+          request_software /            (Request Analysis   |
   yes|  |no            unlock_account / ...             Agent extracts   |
      |  |                    |                        issue/device/action)|
      v  v                    |                               |       |
   answer  continue into      |                               v       |
   directly "device/VPN"      |                    asset_and_ticket_support |
           branch             |                    (instruction: "look up  |
              |                |                     asset + warranty,     |
              +----------------+                     do not create ticket")|
                                                             |               |
                                                             v               |
                                              +----------------------------+ |
                                              |  ASSET & SUPPORT AGENT      | |
                                              |  search_asset -> check_warranty| |
                                              +--------------+-------------+ |
                                                             |               |
                                                             v               |
                                                      notify_user            |
                                                (instruction: "preview the   |
                                                 ticket, ask for             |
                                                 confirmation")              |
                                                             |               |
                                                             v               |
                                              +----------------------------+ |
                                              |   NOTIFICATION AGENT        | |
                                              |   (preview + "yes/no?")     | |
                                              +--------------+-------------+ |
                                                             |               |
                                                    STOP - wait for the      |
                                                    user's reply             |
                                                             |               |
                                              user: "yes, go ahead" ---------+
                                                             |
                                                             v
                                               asset_and_ticket_support
                                          (instruction: "confirmed,
                                              create the ticket now")
                                                             |
                                                             v
                                              +----------------------------+
                                              |  ASSET & SUPPORT AGENT      |
                                              |  create_ticket()            |
                                              +--------------+-------------+
                                                             |
                                                             v
                                                      notify_user
                                            (instruction: "ticket created,
                                              generate the summary")
                                                             |
                                                             v
                                              +----------------------------+
                                              |   NOTIFICATION AGENT        |
                                              |   generate_summary()        |
                                              +--------------+-------------+
                                                             |
                                                             v
                                                final reply to the user
                                        + tooltip: "Agents used: Supervisor,
                                           Request Analysis, Asset & Support,
                                           Notification"
```

Key detail: a hard rule in the Supervisor's system prompt
([supervisor_agent.py:156](../../src/agents/supervisor_agent.py)) forbids
creating the ticket in the same turn as its preview — so the diagram splits
into "turn 1" (analyze -> warranty check -> preview -> stop) and "turn 2"
(after an explicit "yes" -> create ticket -> summary).
