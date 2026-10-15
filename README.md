# DukanMitra

### A Telugu-first AI assistant for small kirana shops

Manage stock, understand profit, track customer credit, and plan purchases through Telugu or English conversation—with owner approval before any business data changes.

Built solo for the **Amazon Developer Hackathon 2026 — Alexa+ track**, using a self-hosted MCP server and a simulated assistant experience in a web app.

[Live Demo](https://dukanmitra.onrender.com) · [Demo Video](YOUR_DEMO_VIDEO_URL) · [Source Code](https://github.com/mangalapurivijayalakshmi/DukanMitra)

> **Try the demo:** No login is required. The free-tier server may take 30–60 seconds to wake up. The hosted app uses demo data, which resets when the server restarts. AI features depend on Gemini API availability and quota.

---

## The problem

Small kirana shop owners often manage inventory, sales, and customer credit—also called *udhar*—using notebooks.

Answering everyday questions can require checking several records:

- What is running out?
- How much profit did I make this week?
- Which customer has overdue dues?
- What should I order tomorrow?
- How should I update stock from a supplier bill?

DukanMitra brings these tasks into a Telugu-first conversational interface, supported by a visual dashboard.

## How it works

**Ask → Analyze → Recommend → Confirm**

1. The owner asks a question in Telugu or English.
2. The agent calls business tools to retrieve relevant records.
3. It returns an answer or recommends an action.
4. If the action changes business data, it asks for explicit owner confirmation before proceeding.

For example:

> **Owner:** రమేష్ కి 2 కిలో చక్కెర ఉద్దెర అమ్మాను  
> *I sold 2 kg of sugar to Ramesh on credit.*
>
> **Assistant:** Presents the proposed sale for review and confirmation.
>
> **Owner:** Confirms.
>
> **App:** Records the sale and updates the related stock and customer credit.

Read-only questions do not require confirmation.

## Key features

### Telugu and English assistant

- Telugu and English chat.
- Telugu voice input using browser speech APIs (`te-IN`).
- Spoken replies using browser speech synthesis.
- Gemini function calling with per-session conversation memory.
- Answers grounded in business tools rather than invented figures.

Voice availability and quality depend on the browser and device.

### Business dashboard

- Revenue, cost of goods, expenses, and net profit shown separately.
- Sales charts with 7-day and 30-day views.
- Best-selling products.
- Low-stock indicators comparing current stock with minimum levels.
- Expiry warnings.
- Stock and billing history through business tools.

### Customer credit management

- Customer balances and credit ageing.
- Colour-coded pending dues.
- Warnings for dues pending more than 30 days.
- Owner-confirmed payment entry.
- WhatsApp reminder links with prefilled messages.

### Stock planning and supplier orders

- Estimated stock-out predictions.
- Suggested reorder quantities.
- Reorder drafts, owner approval, and delivery tracking.
- WhatsApp supplier-order links.
- Festival stock suggestions for Dasara, Diwali, Sankranti, and Ugadi.

Forecasts and suggested quantities are estimates, not guarantees.

### Supplier bill scanning

1. Upload a supplier bill photo.
2. Gemini vision extracts the items and quantities.
3. The owner reviews the extracted information.
4. Stock changes only after owner confirmation.

### Installable web experience

- Mobile-responsive dashboard.
- Installable PWA.
- No login required for the hosted demo.

## Demo video

[Watch the project demonstration](YOUR_DEMO_VIDEO_URL)

The demo covers:

- A Telugu business question.
- A credit sale with owner confirmation.
- Estimated reorder advice.
- Supplier bill scanning and review.
- A working MCP tool call in MCP Inspector.

> Replace `YOUR_DEMO_VIDEO_URL` with the final video link before submission.

## Screenshots

### Dashboard and conversational sale

| Dashboard | Credit sale with confirmation |
|---|---|
| ![DukanMitra dashboard](docs/dashboard.png) | ![Credit sale confirmation in chat](docs/chat-sale.png) |

### Supplier bill to stock entry

| Upload a supplier bill | Review before updating stock |
|---|---|
| ![Supplier bill photo](docs/bill-scan1.png) | ![Extracted bill items awaiting review](docs/bill-scan.png) |

### Mobile and MCP tools

| Mobile interface | MCP Inspector |
|---|---|
| ![Mobile interface](docs/mobile.png) | ![Business tools in MCP Inspector](docs/mcp_inspector.png) |

## MCP server and Alexa+ track approach

DukanMitra includes a self-hosted MCP server implemented in `mcp_server.py`.

- Framework: FastMCP.
- Transport: Streamable HTTP.
- Endpoint: `/mcp`.
- Local port: `8000`.
- Business tools exposed: 20.

The tools cover:

- Stock and pricing.
- Sales and best sellers.
- Customer credit and payments.
- Expenses and profit summaries.
- Stock and bill history.
- Expiry alerts.
- Stock-out prediction and reorder advice.
- Reorder drafting, approval, and delivery.
- Sale recording.

### Simulation boundary

The browser app demonstrates a **simulated Alexa+ assistant experience** powered by Gemini. It is not a live Alexa+ integration.

The web agent calls the shared Python business-tool layer directly. The MCP server exposes that same business logic to MCP clients such as MCP Inspector.

The hosted demo runs the web application. The MCP server is demonstrated separately using the local setup below.

## Architecture

```text
Browser
PWA · Telugu/English chat · Voice input/output
        |
        v
Django views
agent_api/views.py
        |
        v
Gemini agent
agent_api/agent.py
        |
        v
Shared business tools <------------ MCP server
agent_api/tools.py                   mcp_server.py
        |                               ^
        v                               |
Django ORM                         MCP client
        |                         e.g. Inspector
        v
SQLite database
shop/models.py
```

Both interfaces use the same business logic:

```text
Web: Browser → Django → Gemini agent → business tools → database

MCP: MCP client → MCP server → business tools → database
```

### Main files

| File or directory | Responsibility |
|---|---|
| `mcp_server.py` | MCP server and tool exposure |
| `agent_api/tools.py` | Shared business logic |
| `agent_api/agent.py` | Gemini agent and function calling |
| `agent_api/bill.py` | Bill extraction and owner-approved stock entry |
| `agent_api/festival.py` | Festival stock suggestions |
| `agent_api/views.py` | Web views and API endpoints |
| `agent_api/templates/chat.html` | Dashboard and chat interface |
| `shop/models.py` | Business data models |
| `shop/seed_data.py` | Demo data |

## Safety and data integrity

### Owner approval before changes

Data-changing actions require explicit owner confirmation, including:

- Recording a sale.
- Recording a customer payment.
- Adding an expense.
- Approving a reorder.
- Marking an order as delivered.
- Adding stock from a scanned supplier bill.

### Tool-backed numbers

Business figures come from database tools rather than model-generated guesses.

### Clear financial reporting

Revenue is not presented as profit. The dashboard separates:

- Revenue.
- Cost of goods.
- Expenses.
- Net profit.

### Clearly labelled estimates

Stock-out forecasts, reorder quantities, and festival recommendations are estimates based on available demo data.

### Human review of bill extraction

AI-extracted bill information is presented for review before it changes stock.

## Technology stack

| Layer | Technology |
|---|---|
| Backend | Python, Django |
| Demo database | SQLite |
| AI agent | Google Gemini function calling |
| Bill extraction | Gemini vision |
| MCP server | FastMCP, Streamable HTTP |
| Voice | Browser speech recognition and synthesis |
| Messaging handoff | WhatsApp deep links |
| Web experience | Responsive UI, PWA |
| Hosting | Render, Gunicorn |

WhatsApp links open prefilled messages. They do not automatically send messages through the WhatsApp Business API.

## Run locally

Python 3.12 is recommended.

### 1. Clone the repository

```bash
git clone [https://github.com/mangalapurivijayalakshmi/DukanMitra.git](https://github.com/mangalapurivijayalakshmi/DukanMitra.git)
cd DukanMitra
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
```

macOS / Linux:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the environment

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your-gemini-api-key
```

Do not commit API keys or other secrets to the repository.

### 5. Set up the database

```bash
python manage.py migrate
python manage.py shell -c "from shop.seed_data import run; run()"
```

This loads the demonstration dataset.

### 6. Start the MCP server

In terminal 1:

```bash
python mcp_server.py
```

MCP endpoint:

```text
http://127.0.0.1:8000/mcp
```

### 7. Start the web app

In terminal 2, activate the same virtual environment and run:

```bash
python manage.py runserver 8001
```

Open:

```text
http://127.0.0.1:8001
```

### 8. Inspect the MCP tools

With Node.js and npm available, run:

```bash
npx @modelcontextprotocol/inspector
```

In MCP Inspector:

1. Select **Streamable HTTP**.
2. Enter `http://127.0.0.1:8000/mcp`.
3. Connect to the server.
4. Open the tools list.
5. Execute a read-only tool to inspect its response.

## Testing guide for judges

### Hosted web demo

Open [DukanMitra](https://dukanmitra.onrender.com). Allow up to 60 seconds for the initial load.

Try these prompts:

| Telugu prompt | English meaning |
|---|---|
| `ఈ వారం లాభం ఎంత?` | What is this week's profit? |
| `రేపు ఏం కొనాలి?` | What should I buy tomorrow? |
| `ఎవరి బాకీ ఎక్కువ రోజులుగా ఉంది?` | Whose dues have been pending the longest? |
| `రాబోయే పండుగకు ఏం కొనాలి?` | What should I stock for the next festival? |
| `రమేష్ కి 2 కిలో చక్కెర ఉద్దెర అమ్మాను` | I sold 2 kg of sugar to Ramesh on credit. |

### Verify the confirmation flow

1. Note the relevant stock level and customer balance.
2. Request a credit sale.
3. Review the proposed transaction.
4. Confirm that no business data changes before approval.
5. Approve the transaction.
6. Check the updated stock and customer balance.

### Explore the dashboard

- Review sales, profit, and low-stock information.
- Open a customer reminder through WhatsApp.
- Use the payment button to review and confirm a payment.
- Upload a supplier bill photo.
- Review the extracted items before confirming stock entry.

### Test MCP separately

Follow the local setup and connect MCP Inspector to `/mcp`.

The hosted website and local MCP endpoint are separate demonstration surfaces.

## Deployment

The web application is hosted on Render.

### Build command

```bash
pip install -r requirements.txt
```

### Start command

```bash
python manage.py migrate && python manage.py shell -c "from shop.seed_data import run; run()" && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

### Environment variables

```text
GEMINI_API_KEY
SECRET_KEY
DEBUG=False
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
```

Configure hostnames and trusted origins for the deployed environment.

### Demo deployment boundary

- This deployment runs the web app, not the separate MCP server.
- The free-tier service may sleep when idle.
- SQLite demo data is not persistent across hosted restarts.
- The startup command loads demo data.
- This configuration is intended for demonstration, not a production shop.

## Work completed during the hackathon

The following components were built during the hackathon submission period:

- Django data models and demo dataset.
- Shared business-tool layer.
- Self-hosted MCP server.
- Gemini conversational agent.
- Telugu and English chat.
- Dashboard and sales visualisations.
- Customer credit ageing and payment workflows.
- WhatsApp reminder and supplier-order links.
- Supplier bill scanning and review.
- Stock-out estimates and reorder suggestions.
- Festival stock suggestions.
- Browser voice interaction.
- PWA support and hosted deployment.

## Development friction and fallback

Amazon Bedrock was attempted, but model invocation was blocked on the free-plan account used for this project.

Gemini was used for the working agent and bill extraction.

See [the friction log](docs/friction_log.md) for the attempted setup, observed errors, and workaround.

## Current limitations

- Demonstration data only; purchase prices are illustrative.
- No authentication or multi-shop isolation.
- The public demo is a shared, single-shop environment.
- Hosted SQLite data resets when the server restarts.
- AI features depend on Gemini API quota and availability.
- Voice support varies by browser and device.
- Bill extraction can contain errors and requires owner review.
- Forecasts use limited sales history and are not guarantees.
- Festival dates and quantities use a demo calendar and recent sales.
- WhatsApp links require the owner to complete the sending action.
- The MCP server is run separately from the hosted web app.
- The project demonstrates an Alexa+ simulation, not a live Alexa+ integration.

## Future work

- Authentication and shop-level access control.
- PostgreSQL and persistent storage.
- Automated tests for business tools and approval workflows.
- UPI payment links.
- PDF receipts.
- Longer-history demand forecasting.
- More Indian languages.
- Production-ready MCP hosting and access controls.

## Author

**Mangalapuri Vijayalakshmi**

Solo developer of DukanMitra.

[GitHub](https://github.com/mangalapurivijayalakshmi) · [Project repository](https://github.com/mangalapurivijayalakshmi/DukanMitra)

## License

MIT. See [LICENSE](LICENSE).
