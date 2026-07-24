# Level 3 : Simplified Multi-Agent Architecture

A user submits: "My laptop isn't connecting to the company VPN. Create a support ticket and
check if my laptop warranty is still active."
The system should:
1. Understand the issue.
2. Retrieve employee asset details.
3. Check warranty information.
4. Create a support ticket.
5. Ask the user for confirmation.
6. Generate a support summary.
This is intentionally an IT support workflow, not a complete enterprise helpdesk platform.

1. Request Analysis Agent
Responsibilities
- Extract issue type
- Extract device information
- Identify required action
Structured Output


```json
{
    "issue": "VPN Connection",
    "device": "Company Laptop",
    "action": "Create Ticket"
}```

2. Asset & Support Agent
Responsibilities
- Search employee asset from a provided JSON file
- Check warranty information
- Create support ticket
Tools

- search_asset()
●
- check_warranty()
●
create_ticket()

This agent combines asset lookup and ticket creation to keep the lab manageable.

3. Notification Agent
Responsibilities
- Present ticket details
- Ask for confirmation
- Generate support summary

None
Tool

generate_summary()
The tool can simply save the support request to a local JSON file or in-memory list.