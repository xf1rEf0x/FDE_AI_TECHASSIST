# Provider Switching Design (HuggingFace ↔ Gemini)

**Date:** 2026-07-27  
**Status:** Design Approved  
**Scope:** Add UI-driven LLM provider switching between HuggingFace and Gemini

## Overview

Enable users to switch between HuggingFace (DeepSeek-R1) and Gemini (Google) LLM providers directly from the Streamlit sidebar without restarting the app. Both API keys are configured in `.env`. Conversation history persists across provider changes.

## Architecture

### 1. LangChain Integration (`src/langchain_integration.py`)

**New Functions:**
- `get_gemini_api_key() -> str` — Load `GOOGLE_API_KEY` from `.env`, raise `ValueError` if missing

**Modified Functions:**
- `create_langchain_model(temperature: float, provider: str = "huggingface") -> ChatLLM`
  - **Parameter:** `provider` — "huggingface" or "gemini" (case-insensitive)
  - **Logic:**
    - If provider == "huggingface": existing logic (HuggingFaceEndpoint + ChatHuggingFace wrapper)
    - If provider == "gemini": instantiate `ChatGoogleGenerativeAI(model="gemini-pro", temperature=temperature)`, wrap if needed for interface consistency
    - Raise `ValueError` if API key missing for chosen provider
  - **Return:** LLM instance compatible with LangChain prompt templates and LCEL chains

**Rationale:** Single decision point; both providers return compatible interfaces so conversation functions don't branch.

### 2. Conversation Functions (`src/conversation.py`)

**Modified Signatures:**
```python
def get_response(user_message, role, history, temperature=0.7, provider="huggingface") -> str:
def get_response_stream(user_message, role, history, temperature=0.7, provider="huggingface"):
```

**Changes:** Pass `provider` to `create_langchain_model(temperature, provider)`. No other logic changes.

### 3. Streamlit UI (`app.py`)

**Sidebar Settings (after temperature slider):**
- Add provider dropdown:
  ```python
  st.session_state.provider = st.selectbox(
      "LLM Provider:",
      ["HuggingFace", "Gemini"],
      index=0 if st.session_state.get("provider") == "huggingface" else 1
  )
  ```
- Initialize `st.session_state.provider = "huggingface"` on first app load

**Info Box (replaces hardcoded text):**
- Replace: `st.info("🤖 Using HuggingFace model: DeepSeek-R1")`
- With: Dynamic info showing active provider and model name:
  ```python
  if st.session_state.provider == "huggingface":
      st.info("🤖 Using HuggingFace model: DeepSeek-R1")
  else:
      st.info("🤖 Using Gemini model: gemini-pro")
  ```

**Chat Invocation:**
- Pass provider to `get_response_stream()`:
  ```python
  for chunk in get_response_stream(
      user_input, 
      st.session_state.role, 
      st.session_state.messages[:-1], 
      temperature=st.session_state.temperature,
      provider=st.session_state.provider.lower()
  ):
  ```

**Error Handling:**
- Catch `ValueError` in the response block:
  ```python
  except ValueError as e:
      st.error(f"❌ {e}")
  ```
- Error message from `create_langchain_model()` will be clear: "GOOGLE_API_KEY not found..." or "HUGGING_FACE_API not found..."

**Conversation Persistence:**
- No special handling needed; conversation history is preserved in `st.session_state.messages` across provider switches

### 4. Dependencies

**Add to `requirements.txt`:**
```
langchain-google-genai>=0.0.1
google-generativeai>=0.3.0
```

## Data Flow

1. **User selects provider** → Stored in `st.session_state.provider`
2. **User sends message** → UI calls `get_response_stream(..., provider=st.session_state.provider.lower())`
3. **conversation.py** → Calls `create_langchain_model(temperature, provider)`
4. **langchain_integration.py** → Branches on provider, instantiates correct LLM, returns it
5. **LCEL chain** → Executes (prompt | llm), streams response back to UI
6. **History stored** → Message added to `st.session_state.messages` (provider-agnostic)

## Error Cases

| Scenario | Behavior |
|----------|----------|
| User switches to Gemini, `GOOGLE_API_KEY` missing | Catch `ValueError` in app.py, display error to user |
| User switches to HuggingFace, `HUGGING_FACE_API` missing | Catch `ValueError`, display error to user |
| API call fails (rate limit, timeout) | Propagate existing exception handling in chat block |

## Testing Strategy

- **Unit:** `create_langchain_model()` returns correct LLM type per provider parameter
- **Integration:** Conversation functions pass provider through correctly
- **Manual:** Switch providers in UI, verify correct model responds, history persists

## Out of Scope

- Multiple provider requests in parallel
- Provider-specific tuning (e.g., different prompts per provider)
- Fallback logic if primary provider fails
- Analytics on provider usage

## Success Criteria

✓ User can switch providers from sidebar dropdown  
✓ Correct API key is loaded for chosen provider  
✓ Error message shown if API key missing  
✓ Conversation history persists across provider changes  
✓ Chat responds with correct LLM (HuggingFace or Gemini)
