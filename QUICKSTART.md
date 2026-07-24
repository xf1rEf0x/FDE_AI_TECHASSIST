# TechAssist AI Phase 1 - Quick Start

## 5-Minute Setup

### 1. Get API Key (2 min)
Go to [Google AI Studio](https://aistudio.google.com/app/apikeys) and create an API key.

### 2. Setup Project (1 min)
```bash
cd fde_ai_1
pip install -r requirements.txt
cp .env.example .env
```

### 3. Add API Key (1 min)
Edit `.env` and paste your API key:
```
GOOGLE_API_KEY=your_api_key_here
```

### 4. Run App (1 min)
```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## Usage

**Select Role** → Type Question → Get Response

### Try These Scenarios

**As Employee:**
- "I forgot my password, what should I do?"
- "How do I access the VPN?"
- "Can I get Slack installed?"

**As Engineer:**
- "How do I check the asset inventory?"
- "What's our LDAP configuration?"
- "How do I troubleshoot network issues?"

**As Admin:**
- "What are our password policy requirements?"
- "What's the compliance requirement for MFA?"
- "How do we audit user access?"

---

## Run Tests

```bash
# All tests (32 tests, 72% coverage)
pytest tests/ -v

# Quick test
pytest tests/test_prompts.py

# With coverage report
pytest --cov=src --cov-report=term-missing
```

---

## Project Structure

```
fde_ai_1/
├── app.py                 ← Main Streamlit app
├── src/
│   ├── config.py         ← API key loading
│   ├── conversation.py   ← Gemini API calls
│   ├── prompts.py        ← Role-based prompts
│   └── utils.py          ← Message formatting
├── tests/                ← 32 tests
├── README.md             ← Full documentation
├── .env.example          ← Copy to .env, add API key
└── requirements.txt      ← Dependencies
```

---

## Key Features

✅ Role-based personas (employee/engineer/admin)
✅ Real-time streaming responses
✅ Conversation history (within session)
✅ Clean error handling
✅ 32 tests, 72% coverage
✅ Zero database required
✅ Ready for Phase 2 tools

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "API key not found" | Copy `.env.example` to `.env`, add your key |
| "ModuleNotFoundError" | Run `pip install -r requirements.txt` |
| "Port 8501 in use" | Run `streamlit run app.py --server.port 8502` |
| Tests fail | Make sure you're in project root: `cd fde_ai_1` |

---

## Next Steps

1. **Test locally** with different roles and prompts
2. **Refine prompts** based on feedback (edit `src/prompts.py`)
3. **Phase 2**: Add tools (asset lookup, password reset, etc.)
4. **Phase 4**: Deploy to production (auth, logging, persistence)

See **README.md** for full documentation.
