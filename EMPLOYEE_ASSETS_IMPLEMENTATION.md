# Employee Assets Service Implementation

## Overview

Successfully implemented an AI Agent-powered Employee Assets search service in the Employee Assets tab. Users can now interact with the system using natural language to find information about their assigned hardware and software assets.

## Components Implemented

### 1. **Mock Data** (`data/employee_assets.json`)
- 4 sample employees with realistic asset assignments
- Asset types: Laptops, Monitors, Software Licenses, Printers
- Complete asset details: serial numbers, warranty info, purchase dates, status
- Realistic data for testing and demonstration

### 2. **Asset Search Tool** (`src/asset_search_tool.py`)
A LangChain tool that provides multiple search capabilities:

#### Functions:
- `search_assets_by_employee(name, asset_type)` - Find assets by employee name with optional type filtering
- `search_assets_by_serial(serial_number)` - Find assets by serial number or license key
- `search_assets_by_type(asset_type)` - Find all assets of a specific type

#### LangChain Tool:
- `search_employee_assets(query, asset_type)` - Main search tool wrapped as a LangChain tool
- Intelligently searches by name first, then serial number, then type
- Returns formatted results with complete asset information

### 3. **Asset Search Agent** (`src/asset_agent.py`)
An AI Agent built with LangGraph (LangChain 1.3.14) that:

#### Key Features:
- Uses the `create_react_agent` from LangGraph for tool calling
- Custom system prompt tailored for IT asset management
- Handles natural language queries and decides when to use the search tool
- Provides helpful context and recommendations

#### Functions:
- `create_asset_search_agent(temperature)` - Creates and configures the agent
- `search_assets(query, chat_history, temperature)` - Wrapper function for agent invocation

### 4. **UI Integration** (`src/employee_service.py`)
Updated Employee Assets tab with chat-based interface:

#### Features:
- **Conversational Interface**: Users ask questions in natural language
- **Chat History**: Maintains conversation history within the tab session
- **Temperature Control**: Adjustable creativity/determinism (configurable via sidebar)
- **Clear History**: Button to reset conversation
- **Error Handling**: Graceful error messages if search fails

#### Example Queries:
- "Show me my laptop"
- "Find my Microsoft Office license"
- "What monitors do we have assigned?"
- "Who has the MacBook Pro?"

## How It Works

### User Interaction Flow:
1. User opens the "Employee Assets" tab
2. User types a natural language query (e.g., "Show me my monitor")
3. Query is sent to the Asset Search Agent
4. Agent decides to use the `search_employee_assets` tool
5. Tool searches the mock data by:
   - Employee name (if found)
   - Serial number/license key (if not found by name)
   - Asset type (if provided and still no results)
6. Results are formatted and returned to the user
7. Agent provides a helpful response with the findings
8. Conversation is saved in chat history

## Testing

### Test Suite (`tests/test_asset_search_tool.py`)
Comprehensive tests covering:
- Search by employee name (full and partial)
- Search by serial number and license key
- Asset type filtering
- Search by asset type across all employees
- Error handling (no results found)
- LangChain tool invocation

**All 11 asset search tests pass**
**Full test suite: 66 tests pass, 6 skipped**

### Running Tests:
```bash
# Run only asset search tests
pytest tests/test_asset_search_tool.py -v

# Run all tests
pytest tests/ -v
```

## Sample Mock Data

### Employees:
1. **Alice Johnson** (Engineering)
   - MacBook Pro 16" (2023)
   - Dell U2724DE Monitor
   - JetBrains IntelliJ IDEA License

2. **Bob Smith** (Marketing)
   - Dell XPS 15
   - LG 27GN950-B Monitor (4K)
   - HP LaserJet Pro MFP M428fdw Printer

3. **Carol Davis** (Finance)
   - ThinkPad X1 Carbon
   - Microsoft Office 365 License
   - Adobe Creative Suite License

4. **David Wilson** (IT Operations)
   - MacBook Air M2
   - 2x Apple Studio Displays (Retina)

## Architecture

### Tech Stack:
- **Framework**: LangChain 1.3.14 with LangGraph
- **UI**: Streamlit
- **LLM Model**: HuggingFace DeepSeek-R1 (via API)
- **Data Storage**: JSON file (mock data)

### Design Decisions:

1. **Tool-Based Approach**: Used LangChain tools for clean abstraction and reusability
2. **Multiple Search Strategies**: Tool tries different search approaches intelligently
3. **Formatted Output**: Results are beautifully formatted for readability
4. **React Agent**: Used LangGraph's `create_react_agent` for modern tool-calling pattern
5. **Session State**: Chat history maintained in Streamlit session state

## Future Enhancements

- [ ] Integration with real employee database (LDAP/Active Directory)
- [ ] Real asset management API connections
- [ ] Asset comparison tools
- [ ] Warranty/expiry alerts
- [ ] Asset reassignment workflows
- [ ] Hardware recommendation suggestions
- [ ] Export search results to CSV/PDF
- [ ] Advanced filters (department, purchase date range, warranty status)
- [ ] Persistent storage of search results across sessions

## Demo Script

A demo script is available at `test_asset_demo.py`:
```bash
python test_asset_demo.py
```

This demonstrates the agent in action with sample queries.

## Notes

- The asset search tool is idempotent and stateless
- Search is case-insensitive for better UX
- All mock data is in `data/employee_assets.json` and easily replaceable
- The agent gracefully handles ambiguous queries
- Temperature can be adjusted for different response styles (0.0-2.0)
