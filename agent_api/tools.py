import json
from datetime import date, timedelta
from django.db.models import Sum, F
from shop.models import Product, Sale, Customer, ReorderOrder


def _find(name):
    return (
        Product.objects.filter(telugu_name__icontains=name).first()
        or Product.objects.filter(name__icontains=name).first()
    )


def get_stock(product_name: str) -> dict:
    p = _find(product_name)
    if not p:
        return {"found": False, "message": f"'{product_name}' దొరకలేదు"}
    return {"found": True, "product": p.telugu_name, "stock": p.stock,
            "unit": p.unit, "is_low": p.stock < p.low_stock_limit}


def get_price(product_name: str) -> dict:
    p = _find(product_name)
    if not p:
        return {"found": False}
    return {"found": True, "product": p.telugu_name, "price": p.price, "unit": p.unit}


def low_stock_items() -> list:
    items = Product.objects.filter(stock__lt=F("low_stock_limit"))
    return [{"product": p.telugu_name, "stock": p.stock, "unit": p.unit,
             "limit": p.low_stock_limit,
             "supplier": p.supplier.name if p.supplier else None} for p in items]


def today_sales() -> dict:
    qs = Sale.objects.filter(date=date.today())
    total = qs.aggregate(t=Sum("total_amount"))["t"] or 0
    return {"date": str(date.today()), "total_amount": total, "number_of_sales": qs.count()}


def pending_credit() -> list:
    cs = Customer.objects.filter(balance_due__gt=0).order_by("-balance_due")
    return [{"name": c.name, "balance_due": c.balance_due} for c in cs]


def predict_stockout(product_name: str) -> dict:
    p = _find(product_name)
    if not p:
        return {"found": False, "message": f"'{product_name}' దొరకలేదు"}
    since = date.today() - timedelta(days=7)
    sold = Sale.objects.filter(product=p, date__gte=since).aggregate(q=Sum("quantity"))["q"] or 0
    avg = sold / 7
    days_left = round(p.stock / avg, 1) if avg > 0 else None
    return {"found": True, "product": p.telugu_name, "stock": p.stock, "unit": p.unit,
            "daily_average_sales": round(avg, 2), "days_left": days_left}


def draft_reorder() -> list:
    low = Product.objects.filter(stock__lt=F("low_stock_limit")).select_related("supplier")
    by_supplier = {}
    for p in low:
        if not p.supplier:
            continue
        qty = round(p.low_stock_limit * 2 - p.stock, 1)
        by_supplier.setdefault(p.supplier, []).append(
            {"product": p.telugu_name, "quantity": qty, "unit": p.unit})

    drafts = []
    for supplier, items in by_supplier.items():
        lines = "\n".join(f"- {i['product']}: {i['quantity']} {i['unit']}" for i in items)
        message = f"నమస్తే {supplier.name}, దయచేసి ఈ సరుకు పంపండి:\n{lines}"
        order = ReorderOrder.objects.filter(supplier=supplier, status="draft").first()
        if order:
            order.items_json = json.dumps(items, ensure_ascii=False)
            order.message = message
            order.save()
        else:
            order = ReorderOrder.objects.create(
                supplier=supplier, items_json=json.dumps(items, ensure_ascii=False),
                message=message, status="draft")
        drafts.append({"order_id": order.id, "supplier": supplier.name, "items": items,
                       "message": message, "status": "draft"})
    return drafts


def approve_reorder(order_id: int) -> dict:
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
    return {"sales": today_sales(), "low_stock": low_stock_items(),
            "pending_credit": pending_credit()}

def customer_credit(name: str) -> dict:
    c = Customer.objects.filter(name__icontains=name).first()
    if not c:
        return {"found": False, "message": f"'{name}' దొరకలేదు"}
    return {"found": True, "name": c.name, "balance_due": c.balance_due}


def best_sellers(days: int = 7) -> list:
    since = date.today() - timedelta(days=days)
    rows = (Sale.objects.filter(date__gte=since)
            .values("product__telugu_name", "product__unit")
            .annotate(q=Sum("quantity"), amt=Sum("total_amount"))
            .order_by("-amt")[:5])
    return [{"product": r["product__telugu_name"], "quantity": r["q"],
             "unit": r["product__unit"], "revenue": r["amt"]} for r in rows]