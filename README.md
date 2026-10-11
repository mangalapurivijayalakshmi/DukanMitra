# DukanMitra

A Telugu/English voice-and-chat AI agent for small kirana (grocery) shop owners in India.
Built for the **Amazon Developer Hackathon, Alexa+ track**.

The owner asks about stock, prices, sales and customer credit (udhar). The agent calls real tools over a **self-hosted MCP server**, predicts stock-outs, drafts supplier reorders, and **never confirms an order without explicit owner approval**.

## Features
- 9 MCP tools: `get_stock`, `get_price`, `low_stock_items`, `today_sales`, `pending_credit`, `predict_stockout`, `draft_reorder`, `approve_reorder`, `daily_summary`
- MCP server over Streamable HTTP (spec 2025-11-25)
- Web chat UI with Telugu voice input (browser speech recognition, `te-IN`)
- Agentic flow: draft reorder -> owner approval -> approved order message
- Session memory within a conversation

## Architecture
- `mcp_server.py`: MCP server (FastMCP, port 8000, endpoint `/mcp`)
- `agent_api/tools.py`: tool logic (Django ORM)
- `agent_api/agent.py`: Gemini agent with tool calling
- `agent_api/views.py`, `templates/chat.html`: web UI (port 8001)
- `shop/`: models (Product, Sale, Customer, Supplier, ReorderOrder) and `seed_data.py`

## Setup
```bash
git clone https://github.com/mangalapurivijayalakshmi/DukanMitra.git
cd DukanMitra
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```
Create a `.env` file:
```
GEMINI_API_KEY=your-key
```
Create the database and demo data:
```bash
python manage.py migrate
python manage.py shell
>>> from shop.seed_data import run
>>> run()
>>> exit()
```

## Run
Terminal 1 (MCP server):
```bash
python mcp_server.py
```
Test with MCP Inspector: `npx @modelcontextprotocol/inspector`, transport Streamable HTTP, URL `http://127.0.0.1:8000/mcp`.

Terminal 2 (web UI):
```bash
python manage.py runserver 8001
```
Open http://127.0.0.1:8001

## Demo flow
1. "బియ్యం ఎంత ఉంది? ఎన్ని రోజులు వస్తుంది?"
2. "తక్కువ stock ఉన్నవాటికి supplier కి order తయారు చేయి"
3. "అవును, approve చేయి"

## Notes
- LLM: Google Gemini (model set in `agent_api/agent.py`). Amazon Bedrock was attempted but model invocation was blocked on our free-plan account (see `docs/friction_log.md`).
- Demo data only; no real personal data.

## License
MIT
