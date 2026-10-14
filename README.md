# DukanMitra

A Telugu/English voice-and-chat AI agent for small kirana (grocery) shop owners in India.
Built for the **Amazon Developer Hackathon, Alexa+ track** (self-hosted MCP server + simulated assistant experience in a web app).

The owner asks about stock, sales, profit and customer credit in Telugu. The agent calls real tools over an **MCP server**, predicts stock-outs, recommends reorder quantities, and **never changes data without explicit owner confirmation** (Ask -> Analyze -> Recommend -> Confirm).

## Features
- **MCP server** (Streamable HTTP, spec 2025-11-25) exposing 20 tools: stock, price, sales, best sellers, customer credit, payments, expenses, profit summary, stock history, bill history, expiry alerts, stock-out prediction, smart reorder advice, draft/approve/deliver reorders, record sale
- Telugu AI agent with tool calling (Google Gemini) and per-session memory
- Owner approval for orders, with order cards and confirm dialogs
- Dashboard: revenue, cost of goods, expenses, net profit (shown separately), 7/30-day charts, low-stock tags, expiry warnings, customer dues with WhatsApp reminders
- Telugu voice input (`te-IN`) and spoken replies (browser speech APIs)
- Mobile-responsive layout

## Architecture
- `mcp_server.py` - MCP server (FastMCP, port 8000, endpoint `/mcp`)
- `agent_api/tools.py` - business logic (Django ORM), shared by MCP and the web app
- `agent_api/agent.py` - Gemini agent with tool calling
- `agent_api/views.py`, `templates/chat.html` - web UI (port 8001)
- `shop/` - models and `seed_data.py`

## Setup
```bash
git clone https://github.com/mangalapurivijayalakshmi/DukanMitra.git
cd DukanMitra
python -m venv venv
venv\Scripts\activate        # Windows (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```
Create `.env`:
```
GEMINI_API_KEY=your-key
```
Database (SQLite by default, no setup needed):
```bash
python manage.py migrate
python manage.py shell
>>> from shop.seed_data import run
>>> run()
>>> exit()
```
Optional PostgreSQL: set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` in `.env` and `pip install psycopg2-binary`.

## Run
Terminal 1 - MCP server:
```bash
python mcp_server.py
```
Inspect it: `npx @modelcontextprotocol/inspector`, transport **Streamable HTTP**, URL `http://127.0.0.1:8000/mcp`.

Terminal 2 - web app:
```bash
python manage.py runserver 8001
```
Open http://127.0.0.1:8001

## Demo flow
1. "ఈ వారం లాభం ఎంత?" (profit with cost and expenses separated)
2. "రేపు ఏం కొనాలి?" (smart reorder advice, an estimate)
3. Order cards -> approve/cancel
4. "2 కిలోల బియ్యం అమ్మాను" -> confirmation -> bill recorded, stock reduced

## Notes
- Demo data only; purchase prices in `seed_data.py` are illustrative.
- Festival suggestions use a demo calendar, not a live API.
- Stock-out and reorder figures are estimates from the last 7 days of sales.
- Amazon Bedrock was attempted, but model invocation was blocked on our free-plan account (see `docs/friction_log.md`), so Gemini is used.

## Future work
Login and roles, CSV/Excel export, PDF receipts, automated tests, transaction audit views.

## License
MIT
