"""Intent router for detecting user query type and routing to appropriate agent."""

from langchain_google_genai import ChatGoogleGenerativeAI
import json


class IntentRouter:
    """Routes user queries to the appropriate agent based on intent detection."""

    def __init__(self, model_name: str = "gemini-3.5-flash-lite"):
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)

    def detect_intent(self, user_message: str, chat_history: list) -> dict:
        """
        Detect the intent of the user's message.

        Args:
            user_message: The user's input message
            chat_history: List of prior messages for context

        Returns:
            {
                "intent": "helpdesk" | "software_request" | "asset_search" | "unknown",
                "confidence": float (0.0-1.0),
                "clarification": str | None
            }
        """
        prompt = f"""Analyze the user's message and determine which service they need:

PRIORITY RULES:
- If message contains "create ticket", "report", "support ticket", or "issue" → HELPDESK (highest priority)
- If message contains "software", "install", "license", or "app" → SOFTWARE_REQUEST
- If message is ONLY about looking up/finding device info (no action requested) → ASSET_SEARCH

INTENT DEFINITIONS:
1. HELPDESK: Creating/checking IT support tickets, reporting issues, closing tickets
   Keywords: ticket, issue, broken, not working, crash, error, help, support, create ticket, check status

2. SOFTWARE_REQUEST: Requesting software installation, licenses, or managing software requests
   Keywords: software, license, install, application, app, request software, approve, pending requests

3. ASSET_SEARCH: Looking up assigned assets, listing hardware (NOT requesting changes to assets)
   Keywords: show me, what do i have, my assets, list devices, what's assigned
   Examples: "Show me my devices", "What laptop am I assigned to?", "List my hardware"
   Counter-example: "Create a ticket to change my laptop" → HELPDESK (action requested)

User message: "{user_message}"

Chat history context (last 3 messages): {json.dumps(chat_history[-3:]) if chat_history else "None"}

Respond in JSON format with EXACTLY these fields (confidence 0.0-1.0, clarification must be null if confident):
{{
    "intent": "helpdesk" | "software_request" | "asset_search" | "unknown",
    "confidence": 0.0-1.0,
    "clarification": null or a short question only if intent is ambiguous
}}

Only respond with valid JSON, nothing else."""

        response = self.llm.invoke(prompt)
        # Handle both string and list responses (Gemini may return list of content blocks)
        content = response.content
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
                else:
                    text_parts.append(str(item))
            response_text = "".join(text_parts)
        else:
            response_text = content.strip() if isinstance(content, str) else str(content)

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        try:
            result = json.loads(response_text.strip())
            # Ensure clarification is None (not null string or empty) when intent is confident
            if result.get("confidence", 0) >= 0.7 and result.get("intent") != "unknown":
                result["clarification"] = None
            return result
        except json.JSONDecodeError:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "clarification": "I'm not sure what you need. Are you asking about: (1) creating a support ticket, (2) requesting software, or (3) checking your assigned assets?"
            }
