# TechAssist AI - Phase 1: Conversational Chatbot

A role-based IT support chatbot powered by Google Gemini API and Streamlit.

## Overview

TechAssist AI Phase 1 is a simple conversational interface that provides IT support to employees, engineers, and administrators at TechAssist Solutions. The assistant adapts its persona based on the user's role:

- **Employee**: Plain-language guidance for common issues (password resets, VPN, software)
- **Engineer**: Technical depth and infrastructure discussions
- **Admin**: Security, policies, and compliance focus

## Setup

### Prerequisites

- Python 3.10 or higher
- Google API key (get free key from [Google AI Studio](https://aistudio.google.com/app/apikeys))

### Installation

1. **Clone the repository** (if applicable):
   ```bash
   cd fde_ai_1
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API key**:
   ```bash
   cp .env.example .env
   # Edit .env and paste your GOOGLE_API_KEY
   nano .env  # or your preferred editor
   ```

## Usage

### Run the Streamlit app

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

**To use:**
1. Select your role (Employee, Engineer, or Admin) in the sidebar
2. Type your question in the chat input
3. Get a response tailored to your role
4. Clear conversation history with the "Clear Conversation" button

### Run tests

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_prompts.py -v

# Run specific test
pytest tests/test_user_flows.py::TestCriticalUserFlows::test_employee_password_reset_flow -v
```

## Project Structure

```
fde_ai_1/
├── app.py                      # Streamlit UI
├── src/
│   ├── config.py              # Configuration & API key loading
│   ├── conversation.py        # Gemini API integration
│   ├── prompts.py             # Role-based system prompts
│   └── utils.py               # Message formatting utilities
├── tests/
│   ├── conftest.py            # Pytest fixtures & mocks
│   ├── test_prompts.py        # Prompt validation
│   ├── test_utils.py          # Utility function tests
│   ├── test_conversation.py   # API integration tests
│   └── test_user_flows.py     # End-to-end scenarios
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── pytest.ini                 # Pytest configuration
└── README.md                  # This file
```

## Key Features

- **Role-based personas**: Different system prompts for employee, engineer, and admin users
- **Conversation memory**: Full conversation history maintained within a session
- **Real-time streaming**: Responses appear character-by-character for better UX
- **Error handling**: Graceful handling of invalid input and API errors
- **Stateless design**: Easy to extend with Phase 2 tools


## Architecture

The application follows a simple, lazy architecture:

1. **Streamlit UI** (`app.py`) — Handles role selection, chat display, and session state
2. **Conversation Layer** (`conversation.py`) — Stateless wrapper around Gemini API
3. **System Prompts** (`prompts.py`) — Role-based persona definitions
4. **Configuration** (`config.py`) — API key and model selection
5. **Utilities** (`utils.py`) — Message formatting and history management

**Why this design?**
- Minimal dependencies: Only Gemini SDK + Streamlit
- Testable: Conversation layer is a pure function (given input, returns output)
- Extensible: Phase 2 will add tool calling to the conversation layer without changing the UI

## Testing

Phase 1 includes 25+ unit, integration, and e2e tests covering:

- **Prompt validation** (7 tests) — Verify role-based prompts exist and differ
- **Session state management** (6 tests) — History append, retrieval, clearing
- **API integration** (7 tests) — Gemini client initialization, message formatting
- **User flows** (6 tests) — Critical scenarios like password reset, role switching
- **Error handling** (3 tests) — Empty input, invalid roles, missing API keys

**Coverage target**: 75% overall, 85% for source code.

Run tests locally before committing:
```bash
pytest tests/ --cov=src
```

## Configuration

### Environment Variables

- `GOOGLE_API_KEY` (required) — Your Google AI Studio API key
- `GEMINI_MODEL` (optional, default: `gemini-2.0-flash`) — Gemini model to use

## Roadmap

- **Phase 1** (current): Simple chatbot with role-based personas ✓
- **Phase 2**: Single agent with tools (asset lookup, password reset, ticket creation)
- **Phase 3**: Multi-agent system (request analysis, asset support, notifications)
- **Phase 4**: Production deployment (env config, logging, persistence)

## Troubleshooting

### "GOOGLE_API_KEY not found"
- Make sure you copied `.env.example` to `.env`
- Paste your API key into `.env`
- Restart the app: `streamlit run app.py`

### "API quota exceeded"
- Free tier has rate limits. Wait a few minutes before retrying.
- Use a test API key to avoid unexpected charges.

### Tests fail with "No module named 'google.genai'"
- Install dependencies: `pip install -r requirements.txt`
- Verify you're in the correct Python environment: `which python` (or `where python` on Windows)

## Development

### Adding a new role

1. Add the role to `SYSTEM_PROMPTS` dict in `src/prompts.py`
2. Update `src/conversation.py` to handle the new role (it should already work)
3. Add tests in `tests/test_prompts.py` and `tests/test_user_flows.py`

### Updating system prompts

Edit the prompts in `src/prompts.py` and test locally:
```bash
streamlit run app.py
# Select role in sidebar and test responses
```

## License

Internal use only. See CLAUDE.md for project context.

## Support

For questions or issues, see the CLAUDE.md file for project documentation and context.

- ☕ Powered by Gemini, Streamlit, and just the right amount of caffeine.
- 🖨️ Successfully fixes many IT issues—printer problems remain a work in progress.
