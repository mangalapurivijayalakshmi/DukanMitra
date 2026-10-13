from datetime import date, timedelta
from django.db.models import Sum
from shop.models import Sale
from .tools import _find

# ⚠️ తేదీలను పంచాంగంతో సరిచూసుకోండి. కావాలంటే కొత్త పండుగలు జోడించవచ్చు.
FESTIVALS = [
    {"name": "దసరా",    "date": date(2026, 10, 20), "boost": 1.5,
     "items": ["బియ్యం", "నూనె", "చక్కెర", "గోధుమ పిండి"]},
    {"name": "దీపావళి", "date": date(2026, 11, 8),  "boost": 1.6,
     "items": ["చక్కెర", "నూనె", "గోధుమ పిండి", "బిస్కెట్లు"]},
    {"name": "సంక్రాంతి", "date": date(2027, 1, 14), "boost": 1.8,
     "items": ["బియ్యం", "నూనె", "చక్కెర", "గోధుమ పిండి", "కందిపప్పు"]},
    {"name": "ఉగాది",   "date": date(2027, 4, 7),   "boost": 1.5,
     "items": ["చక్కెర", "పసుపు", "కారం", "నూనె", "బియ్యం"]},
]


def festival_advice(window_days: int = 30) -> dict:
    """రాబోయే పండుగకు ఏ వస్తువులు ఎంత కొనాలో అంచనా (గత 7 రోజుల అమ్మకాల ఆధారంగా). ఇది అంచనా మాత్రమే."""
    today = date.today()
    upcoming = [f for f in FESTIVALS
                if today <= f["date"] <= today + timedelta(days=window_days)]
    if not upcoming:
        return {"found": False, "message": "రాబోయే 30 రోజుల్లో పండుగ లేదు"}

    f = min(upcoming, key=lambda x: x["date"])
    since = today - timedelta(days=7)
    items = []
    for name in f["items"]:
        p = _find(name)
        if not p:
            continue
        sold = Sale.objects.filter(product=p, date__gte=since).aggregate(q=Sum("quantity"))["q"] or 0
        weekly = max(sold, p.low_stock_limit)          # సాధారణ వారం అవసరం
        qty = max(round(weekly * f["boost"] - p.stock, 1), 0)
        if qty <= 0:
            continue
        items.append({
            "product": p.telugu_name, "stock": p.stock, "unit": p.unit,
            "suggested_qty": qty,
            "supplier": p.supplier.name if p.supplier else None,
            "supplier_phone": p.supplier.phone if p.supplier else "",
        })
    return {"found": True, "name": f["name"], "date": str(f["date"]),
            "days_left": (f["date"] - today).days,
            "boost_percent": int((f["boost"] - 1) * 100),
            "items": items, "note": "ఇది అంచనా మాత్రమే"}