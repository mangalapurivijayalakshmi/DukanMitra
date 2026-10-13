import json
from google.genai import types
from shop.models import Product, StockMovement
from .agent import MODEL, _get_client
from .tools import _find


def scan_bill(image_bytes: bytes, mime_type: str) -> dict:
    """సప్లయర్ బిల్ ఫోటో నుండి వస్తువులు, పరిమాణాలు చదువుతుంది. స్టాక్ మార్చదు."""
    names = ", ".join(f"{p.telugu_name} ({p.name})" for p in Product.objects.all())
    prompt = (
        "ఇది ఒక కిరాణా సప్లయర్ బిల్ ఫోటో. బిల్‌లోని ప్రతి వస్తువును చదివి, "
        "కింది JSON ఫార్మాట్ లో మాత్రమే ఇవ్వు, వేరే టెక్స్ట్ వద్దు:\n"
        '[{"name": "వస్తువు పేరు", "quantity": సంఖ్య, "unit": "kg/litre/packet/piece"}]\n'
        f"దుకాణంలోని వస్తువులు: {names}\n"
        "బిల్‌లోని వస్తువు ఈ జాబితాలోని దేనికైనా సరిపోతే, ఆ జాబితాలోని తెలుగు పేరునే వాడు. "
        "ధరలు వద్దు, పరిమాణం మాత్రమే. చదవలేనివి వదిలేయి."
    )
    try:
        resp = _get_client().models.generate_content(
            model=MODEL,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        text = resp.text.strip().replace("```json", "").replace("```", "").strip()
        rows = json.loads(text)
    except Exception as e:
        print("scan_bill error:", e)
        return {"success": False, "message": "బిల్ చదవలేకపోయాను. స్పష్టమైన ఫోటో తీసి మళ్ళీ ప్రయత్నించండి."}

    items = []
    for r in rows:
        try:
            qty = float(r.get("quantity", 0))
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        p = _find(str(r.get("name", "")))
        items.append({
            "name": r.get("name", ""),
            "product_id": p.id if p else None,
            "product": p.telugu_name if p else None,
            "quantity": qty,
            "unit": p.unit if p else r.get("unit", ""),
        })
    if not items:
        return {"success": False, "message": "బిల్‌లో వస్తువులు కనిపించలేదు."}
    return {"success": True, "items": items}


def apply_bill(rows: list) -> dict:
    """యజమాని ఆమోదించిన తర్వాత మాత్రమే స్టాక్ పెంచుతుంది."""
    updated = []
    for r in rows:
        try:
            qty = float(r["quantity"])
            p = Product.objects.get(id=int(r["product_id"]))
        except (KeyError, TypeError, ValueError, Product.DoesNotExist):
            continue
        if qty <= 0:
            continue
        p.stock += qty
        p.save()
        StockMovement.objects.create(product=p, change=qty, reason="purchase", ref="bill-photo")
        updated.append({"product": p.telugu_name, "stock": p.stock, "unit": p.unit})
    if not updated:
        return {"success": False, "message": "ఏ వస్తువూ నవీకరించబడలేదు."}
    return {"success": True, "updated": updated}