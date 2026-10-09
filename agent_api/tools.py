from datetime import date
from django.db.models import Sum, F
from shop.models import Product, Sale, Customer
import json
from datetime import timedelta
from shop.models import ReorderOrder

def get_stock(product_name: str) -> dict:
    """ఒక ఉత్పత్తి నిల్వ ఎంత ఉందో చెబుతుంది (తెలుగు లేదా ఇంగ్లీష్ పేరుతో)."""
    p = (
        Product.objects.filter(telugu_name__icontains=product_name).first()
        or Product.objects.filter(name__icontains=product_name).first()
    )
    if not p:
        return {"found": False, "message": f"'{product_name}' దొరకలేదు"}
    return {
        "found": True,
        "product": p.telugu_name,
        "stock": p.stock,
        "unit": p.unit,
        "is_low": p.stock < p.low_stock_limit,
    }


def low_stock_items() -> list:
    """నిల్వ తక్కువగా ఉన్న ఉత్పత్తుల జాబితా."""
    items = Product.objects.filter(stock__lt=F("low_stock_limit"))
    return [
        {
            "product": p.telugu_name,
            "stock": p.stock,
            "unit": p.unit,
            "limit": p.low_stock_limit,
            "supplier": p.supplier.name if p.supplier else None,
        }
        for p in items
    ]


def today_sales() -> dict:
    """ఈ రోజు మొత్తం అమ్మకాలు."""
    total = (
        Sale.objects.filter(date=date.today()).aggregate(t=Sum("total_amount"))["t"]
        or 0
    )
    count = Sale.objects.filter(date=date.today()).count()
    return {"date": str(date.today()), "total_amount": total, "number_of_sales": count}


def pending_credit() -> list:
    """బాకీ ఉన్న కస్టమర్ల జాబితా (udhar)."""
    customers = Customer.objects.filter(balance_due__gt=0).order_by("-balance_due")
    return [{"name": c.name, "balance_due": c.balance_due} for c in customers]

def predict_stockout(product_name: str) -> dict:
    """గత 7 రోజుల సగటు అమ్మకం ప్రకారం stock ఎన్ని రోజులు వస్తుందో లెక్క."""
    p = (
        Product.objects.filter(telugu_name__icontains=product_name).first()
        or Product.objects.filter(name__icontains=product_name).first()
    )
    if not p:
        return {"found": False, "message": f"'{product_name}' దొరకలేదు"}

    since = date.today() - timedelta(days=7)
    sold = (
        Sale.objects.filter(product=p, date__gte=since).aggregate(q=Sum("quantity"))["q"]
        or 0
    )
    daily_avg = sold / 7
    days_left = round(p.stock / daily_avg, 1) if daily_avg > 0 else None
    return {
        "found": True,
        "product": p.telugu_name,
        "stock": p.stock,
        "unit": p.unit,
        "daily_average_sales": round(daily_avg, 2),
        "days_left": days_left,
    }


def draft_reorder() -> list:
    """Low-stock ఉత్పత్తులకు supplier వారీగా order draft తయారు చేస్తుంది. ఇంకా పంపదు."""
    low = Product.objects.filter(stock__lt=F("low_stock_limit")).select_related("supplier")
    by_supplier = {}
    for p in low:
        if not p.supplier:
            continue
        qty = round(p.low_stock_limit * 2 - p.stock, 1)  # లిమిట్ కి రెట్టింపు వరకు
        by_supplier.setdefault(p.supplier, []).append(
            {"product": p.telugu_name, "quantity": qty, "unit": p.unit}
        )

    drafts = []
    for supplier, items in by_supplier.items():
        lines = "\n".join(f"- {i['product']}: {i['quantity']} {i['unit']}" for i in items)
        message = f"నమస్తే {supplier.name}, దయచేసి ఈ సరుకు పంపండి:\n{lines}"
        order = ReorderOrder.objects.create(
            supplier=supplier, items_json=json.dumps(items, ensure_ascii=False),
            message=message, status="draft",
        )
        drafts.append(
            {"order_id": order.id, "supplier": supplier.name, "items": items,
             "message": message, "status": "draft"}
        )
    return drafts


def approve_reorder(order_id: int) -> dict:
    """Owner ఒప్పుకున్నాకే order ని approve చేస్తుంది."""
    try:
        order = ReorderOrder.objects.get(id=order_id)
    except ReorderOrder.DoesNotExist:
        return {"success": False, "message": f"Order #{order_id} దొరకలేదు"}
    if order.status != "draft":
        return {"success": False, "message": f"Order ఇప్పటికే {order.status}"}
    order.status = "approved"
    order.save()
    return {"success": True, "order_id": order.id, "supplier": order.supplier.name,
            "status": "approved", "message_to_send": order.message}


def daily_summary() -> dict:
    """ఈ రోజు అమ్మకాలు, తక్కువ stock, బాకీలు ఒకే చోట."""
    return {
        "sales": today_sales(),
        "low_stock": low_stock_items(),
        "pending_credit": pending_credit(),
    }