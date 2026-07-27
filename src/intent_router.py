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
        
1. HELPDESK: Creating/checking IT support tickets, reporting issues, closing tickets
   Keywords: ticket, issue, broken, not working, crash, error, help, support, create ticket, check status
   
2. SOFTWARE_REQUEST: Requesting software installation, licenses, or managing software requests
   Keywords: software, license, install, application, app, request software, approve, pending requests
   
3. ASSET_SEARCH: Looking up assigned assets (laptop, monitor, printer, license, hardware)
   Keywords: laptop, desktop, monitor, printer, asset, device, hardware, assigned to, my hardware, what do i have

User message: "{user_message}"

Chat history context (last 3 messages): {json.dumps(chat_history[-3:]) if chat_history else "None"}

Respond in JSON format:
{{
    "intent": "helpdesk" | "software_request" | "asset_search" | "unknown",
    "confidence": 0.0-1.0,
    "clarification": null or a short question if intent is ambiguous
}}

Only respond with valid JSON."""

        try:
            response = self.llm.invoke(prompt)
            # Parse JSON from response
            response_text = response.content.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            result = json.loads(response_text.strip())
            return result
        except Exception:
            # Default to unknown if parsing fails
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "clarification": "I'm not sure what you need. Are you asking about: (1) creating a support ticket, (2) requesting software, or (3) checking your assigned assets?"
            }
