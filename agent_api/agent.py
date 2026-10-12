import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from . import tools

load_dotenv()

MODEL = "gemini-3.5-flash-lite"   # LLM మార్చాలంటే ఇక్కడ మాత్రమే

SYSTEM_PROMPT = """నువ్వు DukanMitra, కిరాణా దుకాణదారుల కోసం తెలుగు AI సహాయకుడివి.
- ఎల్లప్పుడూ సరళమైన తెలుగులో, చిన్నగా సమాధానం ఇవ్వు.
- స్టాక్, ధర, అమ్మకాలు, బాకీల గురించి అడిగితే తప్పనిసరిగా tools వాడు. సంఖ్యలు ఊహించకు.
- reorder కోసం ముందు draft_reorder వాడి, order వివరాలు చూపించు.
- యజమాని స్పష్టంగా 'అవును / ఒప్పుకుంటున్నాను' అంటేనే approve_reorder వాడు. అడగకుండా ఎప్పుడూ approve చేయకు.
"""


def get_stock(product_name: str) -> dict:
    """ఒక ఉత్పత్తి నిల్వ ఎంత ఉందో చెబుతుంది (తెలుగు లేదా ఇంగ్లీష్ పేరు)."""
    return tools.get_stock(product_name)

def get_price(product_name: str) -> dict:
    """ఒక ఉత్పత్తి ధర చెబుతుంది."""
    return tools.get_price(product_name)

def low_stock_items() -> list:
    """నిల్వ తక్కువగా ఉన్న ఉత్పత్తుల జాబితా."""
    return tools.low_stock_items()

def today_sales() -> dict:
    """ఈ రోజు మొత్తం అమ్మకాలు."""
    return tools.today_sales()

def pending_credit() -> list:
    """బాకీ ఉన్న కస్టమర్ల జాబితా."""
    return tools.pending_credit()

def predict_stockout(product_name: str) -> dict:
    """గత 7 రోజుల అమ్మకాల ప్రకారం stock ఎన్ని రోజులు వస్తుందో లెక్క."""
    return tools.predict_stockout(product_name)

def draft_reorder() -> list:
    """Low-stock ఉత్పత్తులకు supplier order draft తయారు చేస్తుంది. పంపదు."""
    return tools.draft_reorder()

def approve_reorder(order_id: int) -> dict:
    """యజమాని స్పష్టంగా ఒప్పుకున్నాకే మాత్రమే order ని approve చేస్తుంది."""
    return tools.approve_reorder(order_id)

def daily_summary() -> dict:
    """ఈ రోజు అమ్మకాలు, తక్కువ stock, బాకీలు ఒకే summary లో."""
    return tools.daily_summary()

def customer_credit(name: str) -> dict:
    """ఒక కస్టమర్ ఎంత బాకీ ఉన్నాడో చెబుతుంది (పేరుతో)."""
    return tools.customer_credit(name)

def best_sellers(days: int = 7) -> list:
    """గత కొన్ని రోజుల్లో ఎక్కువగా అమ్ముడైన వస్తువులు."""
    return tools.best_sellers(days)

def record_sale(product_name: str, quantity: float) -> dict:
    """యజమాని చెప్పిన అమ్మకాన్ని నమోదు చేస్తుంది, stock తగ్గిస్తుంది, మొత్తం లెక్కిస్తుంది."""
    return tools.record_sale(product_name, quantity)

TOOL_LIST = [get_stock, get_price, low_stock_items, today_sales, pending_credit,
             predict_stockout, draft_reorder, approve_reorder, daily_summary,
             customer_credit, best_sellers,
             tools.record_sale, tools.record_payment, tools.add_expense,
             tools.profit_summary, tools.smart_reorder_advice, tools.mark_delivered,
             tools.expiry_alerts, tools.stock_history, tools.bill_history]

_client = None
_chats = {}


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def chat(session_id: str, message: str) -> str:
    if session_id not in _chats:
        _chats[session_id] = _get_client().chats.create(
            model=MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=TOOL_LIST,
            ),
        )
    response = _chats[session_id].send_message(message)
    return response.text 

SYSTEM_PROMPT

- డేటా మార్చే చర్యలకు (record_sale, record_payment, add_expense, approve_reorder, mark_delivered) ముందు వివరాలు చెప్పి "అవునా?" అని అడుగు. యజమాని స్పష్టంగా అవును అన్నాకే ఆ tool వాడు.
- లాభం గురించి అడిగితే profit_summary వాడు. Revenue ని లాభం అనకు. warning ఉంటే చెప్పు.
- 'రేపు ఏం కొనాలి' అంటే smart_reorder_advice వాడి, ఇది అంచనా మాత్రమే అని చెప్పు.