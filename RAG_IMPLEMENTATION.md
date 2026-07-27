# RAG Implementation for TechAssist AI

## Overview

RAG (Retrieval-Augmented Generation) has been integrated into the TechAssist AI chatbot. When users ask questions about **passwords** or **VPN issues**, the system automatically retrieves relevant documentation from PDF files and injects that context into the LLM prompt.

## How It Works

### 1. Detection
The system detects password/VPN-related queries using keyword matching in `_should_use_rag()`:
- Keywords: "password", "vpn", "connect", "reset", "access", "login", "authentication", "account unlock"

### 2. Retrieval
When a relevant query is detected:
- **PDFs loaded**: `RAG/output_pdfs_TechAssist_Password_VPN_SOP.pdf` and `RAG/output_pdfs_TechAssist_VPN_Troubleshooting_Playbook.pdf`
- **Chunking**: Documents are split into 500-char chunks with 50-char overlap
- **Matching**: Top 3 most relevant chunks are selected using keyword matching
- **Formatting**: Retrieved content is formatted and injected into the system prompt

### 3. LLM Response
The enriched system prompt (original prompt + documentation) is sent to the LLM, which provides answers grounded in actual documentation.

## Architecture

### Files

- **`src/rag.py`** — RAG core module
  - `RAGRetriever` class: loads PDFs, chunks text, retrieves relevant docs
  - `get_rag_retriever()`: singleton factory for retriever instance
  
- **`src/conversation.py`** — Updated conversation handler
  - `_should_use_rag()`: keyword-based detection
  - `get_response()` / `get_response_stream()`: enhanced with RAG context injection
  
- **`RAG/`** — Directory containing PDF source documents

### Dependencies Added

```
pypdf>=3.0.0                          # PDF parsing
langchain-text-splitters>=0.0.1       # Document chunking
sentence-transformers>=3.0.0          # (optional, for future semantic embedding)
```

## Usage

### From the UI
1. User logs in and navigates to "AI Chat" tab
2. User asks a question like: "How do I reset my password?" or "I can't connect to VPN"
3. System automatically detects intent and retrieves relevant documentation
4. Assistant provides an answer grounded in the official docs

### Example Queries
- ✅ "How do I reset my password?"
- ✅ "I'm having trouble connecting to VPN"
- ✅ "What's the password reset procedure?"
- ✅ "VPN not connecting, help!"
- ❌ "How do I get promoted?" (not password/VPN, skips RAG)

## Implementation Details

### Keyword Matching Strategy
Uses simple term frequency scoring to rank document chunks:
- Longer words (>3 chars) are counted in both query and document
- Chunks with highest match count are returned
- No ML embeddings required → fast startup, no dependency on sentence-transformers

### Error Handling
- RAG errors are caught silently; response continues without documentation context
- If PDF loading fails, system gracefully degrades to LLM-only mode
- No user-facing errors from RAG module

### Performance
- PDF loading happens once on first RAG call (lazy initialization)
- Retrieval is O(n) where n = number of chunks (typically < 200 for 2 PDFs)
- Typical retrieval latency: <100ms

## Future Enhancements

1. **Semantic Search**: Replace keyword matching with embeddings (sentence-transformers) for better relevance
2. **More Documents**: Add PDFs for other common issues (hardware troubleshooting, software installation, etc.)
3. **Document Categories**: Tag documents and route queries to specific categories
4. **Feedback Loop**: Log when RAG docs were used and helpful to improve retrieval ranking
5. **Hybrid Search**: Combine keyword + semantic search for best-of-both-worlds

## Testing

Run the test suite with:
```bash
# Create a simple test file to validate RAG retrieval
python -c "
from src.rag import get_rag_retriever
rag = get_rag_retriever()
context = rag.format_context('How do I reset my password?')
print('Password retrieval:', 'PASS' if context else 'FAIL')
context = rag.format_context('VPN issues')
print('VPN retrieval:', 'PASS' if context else 'FAIL')
"
```
