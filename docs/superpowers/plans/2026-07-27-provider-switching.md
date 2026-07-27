# Provider Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a sidebar dropdown to switch between HuggingFace and Gemini LLM providers, with conversation history persisting across switches.

**Architecture:** Add a `provider` parameter to the LLM factory function (`create_langchain_model`) that branches to the appropriate provider's LangChain integration, expose provider selection in the Streamlit UI sidebar, pass the chosen provider through the conversation pipeline.

**Tech Stack:** Streamlit, LangChain, LangChain-Google-GenAI, python-dotenv

## Global Constraints

- Both `GOOGLE_API_KEY` (Gemini) and `HUGGING_FACE_API` (HuggingFace) must be in `.env`
- Provider parameter is case-insensitive (`"huggingface"` or `"gemini"`)
- Default provider is HuggingFace
- Conversation history persists across provider switches (no clearing)
- Missing API key raises `ValueError` with clear message
- UI catches and displays error to user via `st.error()`

---

## Task 1: Add Gemini API Key Loader

**Files:**
- Modify: `src/langchain_integration.py:30-50`

**Interfaces:**
- Produces: `get_gemini_api_key() -> str` — loads `GOOGLE_API_KEY` from env, raises `ValueError` if missing

**Steps:**

- [ ] **Step 1: Add Gemini API key getter function**

Add this function after `get_huggingface_api_key()` in `src/langchain_integration.py`:

```python
def get_gemini_api_key() -> str:
    """Load GOOGLE_API_KEY from .env or environment.

    Returns:
        Gemini API key

    Raises:
        ValueError: If key is not found
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found. Please set it in .env or environment variables."
        )
    return api_key
```

- [ ] **Step 2: Verify function is defined**

Run: `python -c "from src.langchain_integration import get_gemini_api_key; print('OK')"`

Expected: Prints `OK`

- [ ] **Step 3: Commit**

```bash
git add src/langchain_integration.py
git commit -m "feat: add gemini api key loader"
```

---

## Task 2: Update Create Langchain Model with Provider Parameter

**Files:**
- Modify: `src/langchain_integration.py:1-55`

**Interfaces:**
- Consumes: `get_gemini_api_key() -> str` (from Task 1)
- Produces: `create_langchain_model(temperature: float, provider: str = "huggingface")` — returns LLM instance compatible with LangChain LCEL chains

**Steps:**

- [ ] **Step 1: Add import for ChatGoogleGenerativeAI**

At the top of `src/langchain_integration.py`, add:

```python
from langchain_google_genai import ChatGoogleGenerativeAI
```

Your imports section should now look like:

```python
import os
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
```

- [ ] **Step 2: Update create_langchain_model signature and add branching logic**

Replace the entire `create_langchain_model` function with:

```python
def create_langchain_model(temperature: float = 0.7, provider: str = "huggingface"):
    """Initialize LLM model via LangChain based on chosen provider.

    Args:
        temperature: Model temperature (0.0 - 2.0)
        provider: "huggingface" or "gemini" (case-insensitive)

    Returns:
        LLM instance (ChatHuggingFace or ChatGoogleGenerativeAI) compatible with LCEL chains

    Raises:
        ValueError: If provider is unknown or API key is missing
    """
    provider = provider.lower().strip()

    if provider == "huggingface":
        api_key = get_huggingface_api_key()
        hf_llm = HuggingFaceEndpoint(
            repo_id="deepseek-ai/DeepSeek-R1:novita",
            huggingfacehub_api_token=api_key,
            temperature=temperature,
        )
        model = ChatHuggingFace(llm=hf_llm)
        return model

    elif provider == "gemini":
        api_key = get_gemini_api_key()
        model = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=temperature,
            google_api_key=api_key,
        )
        return model

    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'huggingface' or 'gemini'.")
```

- [ ] **Step 3: Verify both branches work**

Test HuggingFace branch:
```bash
python -c "from src.langchain_integration import create_langchain_model; m = create_langchain_model(0.7, 'huggingface'); print(f'HF model: {type(m).__name__}')"
```
Expected: Prints `HF model: ChatHuggingFace`

Test Gemini branch:
```bash
python -c "from src.langchain_integration import create_langchain_model; m = create_langchain_model(0.7, 'gemini'); print(f'Gemini model: {type(m).__name__}')"
```
Expected: Prints `Gemini model: ChatGoogleGenerativeAI`

- [ ] **Step 4: Test error case (missing Gemini key)**

Temporarily remove `GOOGLE_API_KEY` from `.env`:
```bash
python -c "from src.langchain_integration import create_langchain_model; create_langchain_model(0.7, 'gemini')" 2>&1
```
Expected: Raises `ValueError: GOOGLE_API_KEY not found...`

Then restore `GOOGLE_API_KEY` to `.env`.

- [ ] **Step 5: Commit**

```bash
git add src/langchain_integration.py
git commit -m "feat: add provider parameter to create_langchain_model with gemini support"
```

---

## Task 3: Add Provider Parameter to Conversation Functions

**Files:**
- Modify: `src/conversation.py:8-89`

**Interfaces:**
- Consumes: `create_langchain_model(temperature, provider) -> LLM`
- Produces:
  - `get_response(user_message: str, role: str, history: list, temperature: float, provider: str) -> str`
  - `get_response_stream(user_message: str, role: str, history: list, temperature: float, provider: str)` — yields text chunks

**Steps:**

- [ ] **Step 1: Update get_response function signature**

Replace the `get_response` function signature and its call to `create_langchain_model`:

```python
def get_response(user_message: str, role: str, history: list[dict], temperature: float = 0.7, provider: str = "huggingface") -> str:
    """Get response from LLM via LangChain.

    Args:
        user_message: The user's latest message
        role: User role ("employee", "engineer", or "admin")
        history: List of previous messages in format [{"role": "user"/"assistant", "content": "..."}]
        temperature: Temperature for response generation (0.0 - 2.0)
        provider: "huggingface" or "gemini"

    Returns:
        Assistant response string

    Raises:
        ValueError: If role is unknown or API key is missing
        Exception: If LLM call fails
    """
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty")

    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    system_prompt = get_system_prompt(role)
    model = create_langchain_model(temperature, provider)

    # Build chat prompt with system instruction
    system_msg = SystemMessagePromptTemplate.from_template(system_prompt)
    human_msg = HumanMessagePromptTemplate.from_template("{user_input}")
    chat_prompt = ChatPromptTemplate.from_messages([system_msg, human_msg])

    # Create runnable chain
    chain = chat_prompt | model

    # Invoke chain and get response
    response = chain.invoke({"user_input": user_message})
    return response.content
```

- [ ] **Step 2: Update get_response_stream function signature**

Replace the `get_response_stream` function signature and its call to `create_langchain_model`:

```python
def get_response_stream(user_message: str, role: str, history: list[dict], temperature: float = 0.7, provider: str = "huggingface"):
    """Get streaming response from LLM via LangChain.

    Yields text chunks as they arrive from the API.

    Args:
        user_message: The user's latest message
        role: User role ("employee", "engineer", or "admin")
        history: List of previous messages (used for context, not actively consumed in this version)
        temperature: Temperature for response generation (0.0 - 2.0)
        provider: "huggingface" or "gemini"

    Yields:
        Text chunks from the response

    Raises:
        ValueError: If role is unknown
    """
    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty")

    if role not in get_available_roles():
        raise ValueError(f"Unknown role: {role}")

    system_prompt = get_system_prompt(role)
    llm = create_langchain_model(temperature, provider)

    # Build chat prompt
    system_msg = SystemMessagePromptTemplate.from_template(system_prompt)
    human_msg = HumanMessagePromptTemplate.from_template("{user_input}")
    chat_prompt = ChatPromptTemplate.from_messages([system_msg, human_msg])

    # Create runnable chain
    chain = chat_prompt | llm

    # For streaming, invoke chain and yield the response
    response = chain.invoke({"user_input": user_message})
    text = response.content

    # Simulate streaming by yielding the response in chunks
    chunk_size = 20
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
```

- [ ] **Step 3: Verify functions accept provider parameter**

Run:
```bash
python -c "from src.conversation import get_response, get_response_stream; import inspect; print('get_response params:', list(inspect.signature(get_response).parameters.keys())); print('get_response_stream params:', list(inspect.signature(get_response_stream).parameters.keys()))"
```

Expected output includes `provider` in both parameter lists.

- [ ] **Step 4: Commit**

```bash
git add src/conversation.py
git commit -m "feat: add provider parameter to conversation functions"
```

---

## Task 4: Add Gemini Dependencies to requirements.txt

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: (existing dependencies)
- Produces: Updated `requirements.txt` with Gemini packages

**Steps:**

- [ ] **Step 1: Add dependencies**

Open `requirements.txt` and add these two lines at the end (after the existing langchain entries):

```
langchain-google-genai>=0.0.1
google-generativeai>=0.3.0
```

Your final `requirements.txt` should look like:

```
streamlit>=1.54.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-cov>=4.1.0
langchain>=0.1.0
langchain-community>=0.1.0
langchain-huggingface>=0.0.1
huggingface-hub>=0.20.0
langchain-google-genai>=0.0.1
google-generativeai>=0.3.0
```

- [ ] **Step 2: Install dependencies**

Run:
```bash
pip install -r requirements.txt
```

Expected: No errors; both packages installed.

- [ ] **Step 3: Verify imports work**

Run:
```bash
python -c "from langchain_google_genai import ChatGoogleGenerativeAI; print('OK')"
```

Expected: Prints `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add langchain-google-genai and google-generativeai dependencies"
```

---

## Task 5: Add Provider Dropdown to Sidebar

**Files:**
- Modify: `app.py:85-120` (sidebar settings section)

**Interfaces:**
- Consumes: `get_response_stream(..., provider: str)` (from Task 3)
- Produces: `st.session_state.provider` — string ("huggingface" or "gemini")

**Steps:**

- [ ] **Step 1: Initialize provider state**

In `app.py`, find the section where session state is initialized (around line 74-89). After the existing initializations, add:

```python
if "provider" not in st.session_state:
    st.session_state.provider = "huggingface"
```

The initialization block should now look like:

```python
# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Role is now bound to logged-in user's role, not settable
current_user = get_current_user()
if current_user:
    st.session_state.role = current_user.get("role", "employee")

if "template_selected" not in st.session_state:
    st.session_state.template_selected = None

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7

if "provider" not in st.session_state:
    st.session_state.provider = "huggingface"
```

- [ ] **Step 2: Add provider dropdown in sidebar**

In the sidebar settings section (around line 92-115), find the temperature slider. After the temperature slider block, add:

```python
    # Provider selector
    st.session_state.provider = st.selectbox(
        "LLM Provider:",
        ["HuggingFace", "Gemini"],
        index=0 if st.session_state.provider.lower() == "huggingface" else 1,
        help="Switch between HuggingFace (DeepSeek-R1) and Gemini (Google)"
    )
```

Your sidebar settings section should now look like:

```python
    # Temperature slider
    st.session_state.temperature = st.slider(
        "Temperature:",
        min_value=0.0,
        max_value=2.0,
        value=st.session_state.temperature,
        step=0.1,
        help="Lower = more focused/deterministic, Higher = more creative/random"
    )

    # Provider selector
    st.session_state.provider = st.selectbox(
        "LLM Provider:",
        ["HuggingFace", "Gemini"],
        index=0 if st.session_state.provider.lower() == "huggingface" else 1,
        help="Switch between HuggingFace (DeepSeek-R1) and Gemini (Google)"
    )

    # Show current role info
    with st.expander("ℹ️ About your role"):
        st.markdown(get_system_prompt(st.session_state.role))
```

- [ ] **Step 3: Test the dropdown appears**

Run:
```bash
streamlit run app.py
```

Expected: Login, then look at sidebar under Settings. Provider dropdown should appear below Temperature slider.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add provider selector dropdown to sidebar"
```

---

## Task 6: Update Dynamic Info Box to Show Active Provider

**Files:**
- Modify: `app.py:105-106` (info box)

**Interfaces:**
- Consumes: `st.session_state.provider` (from Task 5)
- Produces: (UI side effect)

**Steps:**

- [ ] **Step 1: Replace hardcoded info box with dynamic version**

Find the line in the sidebar settings (around line 105) that says:

```python
    st.info("🤖 Using HuggingFace model: DeepSeek-R1")
```

Replace it with:

```python
    if st.session_state.provider.lower() == "huggingface":
        st.info("🤖 Using HuggingFace model: DeepSeek-R1")
    else:
        st.info("🤖 Using Gemini model: gemini-pro")
```

- [ ] **Step 2: Test the info box updates when you switch providers**

Run:
```bash
streamlit run app.py
```

Login, then in the sidebar, select different providers from the dropdown. The info box should update accordingly.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: show active provider in sidebar info box"
```

---

## Task 7: Pass Provider to get_response_stream in Chat Block

**Files:**
- Modify: `app.py:226` (chat invocation)

**Interfaces:**
- Consumes: `st.session_state.provider` (from Task 5), `get_response_stream(..., provider: str)` (from Task 3)
- Produces: (conversation stream to UI)

**Steps:**

- [ ] **Step 1: Update the get_response_stream call to include provider**

In the chat block (around line 226), find the line:

```python
                for chunk in get_response_stream(user_input, st.session_state.role, st.session_state.messages[:-1], temperature=st.session_state.temperature):
```

Replace it with:

```python
                for chunk in get_response_stream(user_input, st.session_state.role, st.session_state.messages[:-1], temperature=st.session_state.temperature, provider=st.session_state.provider.lower()):
```

- [ ] **Step 2: Test the chat uses the selected provider**

Run:
```bash
streamlit run app.py
```

Login, select HuggingFace in the sidebar, send a message. It should respond with DeepSeek. Then switch to Gemini and send another message. It should use Gemini (responses will differ in style/model behavior).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: pass provider parameter to get_response_stream"
```

---

## Task 8: End-to-End Test and Error Handling

**Files:**
- Test: `app.py` (manual testing)

**Interfaces:**
- Consumes: All prior tasks
- Produces: Verified working feature

**Steps:**

- [ ] **Step 1: Test happy path (HuggingFace → Gemini → HuggingFace)**

Run:
```bash
streamlit run app.py
```

Login with demo credentials.

1. Sidebar shows "HuggingFace" selected by default
2. Sidebar info box shows "Using HuggingFace model: DeepSeek-R1"
3. Send a chat message, get response from HuggingFace
4. Switch to Gemini in dropdown
5. Sidebar info box updates to "Using Gemini model: gemini-pro"
6. Send another message, get response from Gemini
7. Scroll up — both messages still in conversation history
8. Switch back to HuggingFace, send a message, response comes from HuggingFace again

Expected: All steps succeed; conversation history persists across switches.

- [ ] **Step 2: Test missing Gemini API key error**

Temporarily remove `GOOGLE_API_KEY` from `.env`:

```bash
# Edit .env, comment out GOOGLE_API_KEY line
```

Restart Streamlit:

```bash
streamlit run app.py
```

Login, switch to Gemini, send a message.

Expected: Error appears in UI: "❌ GOOGLE_API_KEY not found. Please set it in .env or environment variables."

UI remains functional; user can switch back to HuggingFace and chat normally.

Restore `GOOGLE_API_KEY` to `.env`.

- [ ] **Step 3: Test conversation persistence**

Login, start a conversation with HuggingFace (send 2-3 messages).

Switch to Gemini mid-conversation.

Scroll up — all previous HuggingFace messages still there.

Send a message with Gemini active.

Switch back to HuggingFace.

Expected: Full history visible, no messages lost.

- [ ] **Step 4: Verify no test regressions**

Run existing tests:

```bash
pytest tests/ -v
```

Expected: All pass (no new tests added; conversation functions still work with default provider="huggingface").

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "test: verify provider switching e2e and error handling"
```

---

## Self-Review

**Spec Coverage:**
- ✓ Section 1 (LangChain Integration): Tasks 1-2 add Gemini loader and provider branching
- ✓ Section 2 (Conversation Functions): Task 3 adds provider parameter
- ✓ Section 3 (Streamlit UI): Tasks 5-7 add dropdown, state, dynamic info, provider passing
- ✓ Section 4 (Dependencies): Task 4 adds langchain-google-genai
- ✓ Section 4 (Error Handling): Task 8 tests missing API key, error message display

**Placeholder Scan:**
- No TBD, TODO, or "implement later" — all code provided in full
- No "add validation" or "handle errors" without examples — error handling shown in Task 8

**Type Consistency:**
- `provider` parameter type: `str` (case-insensitive)
- Default value: `"huggingface"`
- Valid values: `"huggingface"` (lowercase), `"gemini"` (lowercase)
- Streamlit dropdown stores `"HuggingFace"` or `"Gemini"` (title case), converted with `.lower()` before passing

**No Missing Tasks:**
- All spec sections have corresponding implementation tasks
- No orphaned requirements
