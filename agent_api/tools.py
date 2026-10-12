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
        qty = _suggest_qty(p)
        if qty <= 0:
            continue
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

def record_sale(product_name: str, quantity: float, payment_method: str = "cash", customer_name: str = "") -> dict:
    """అమ్మకాన్ని నమోదు చేస్తుంది: bill number, stock తగ్గింపు, మొత్తం. payment_method: cash, upi లేదా credit (ఉద్దెర కి customer_name తప్పనిసరి)."""
    p = _find(product_name)
    if not p:
        return {"success": False, "message": f"'{product_name}' దొరకలేదు"}
    if quantity <= 0:
        return {"success": False, "message": "పరిమాణం సరిగా లేదు"}
    if p.stock < quantity:
        return {"success": False, "message": f"నిల్వ సరిపోదు, ఉన్నది {p.stock} {p.unit}"}
    cust = None
    if payment_method == "credit":
        cust = Customer.objects.filter(name__icontains=customer_name).first() if customer_name else None
        if not cust:
            return {"success": False, "message": "ఉద్దెర అమ్మకానికి కస్టమర్ పేరు కావాలి"}
    total = quantity * p.price
    sale = Sale.objects.create(product=p, quantity=quantity, total_amount=total,
                               date=date.today(), payment_method=payment_method)
    sale.bill_no = f"B{sale.id:05d}"
    sale.save()
    p.stock -= quantity
    p.save()
    StockMovement.objects.create(product=p, change=-quantity, reason="sale", ref=sale.bill_no)
    if cust:
        cust.balance_due += total
        cust.save()
    return {"success": True, "bill_no": sale.bill_no, "product": p.telugu_name,
            "quantity": quantity, "unit": p.unit, "total": total,
            "payment_method": payment_method, "stock_left": p.stock}


def record_payment(customer_name: str, amount: float, method: str = "cash") -> dict:
    """కస్టమర్ చెల్లించిన బాకీ (పూర్తి లేదా కొంత) నమోదు చేసి balance తగ్గిస్తుంది."""
    c = Customer.objects.filter(name__icontains=customer_name).first()
    if not c:
        return {"success": False, "message": f"'{customer_name}' దొరకలేదు"}
    if amount <= 0 or amount > c.balance_due:
        return {"success": False, "message": f"మొత్తం సరిగా లేదు. బాకీ ₹{c.balance_due}"}
    c.balance_due -= amount
    c.save()
    Payment.objects.create(customer=c, amount=amount, method=method)
    return {"success": True, "customer": c.name, "paid": amount, "balance_left": c.balance_due}


def add_expense(name: str, amount: float) -> dict:
    """ఒక ఖర్చును (అద్దె, కరెంటు, జీతం మొదలైనవి) ఈ రోజు తేదీతో నమోదు చేస్తుంది."""
    if amount <= 0:
        return {"success": False, "message": "మొత్తం సరిగా లేదు"}
    Expense.objects.create(name=name, amount=amount, date=date.today())
    return {"success": True, "name": name, "amount": amount}


def profit_summary(days: int = 7) -> dict:
    """గత N రోజుల Revenue, వస్తువుల cost, ఖర్చులు, gross profit, net profit."""
    since = date.today() - timedelta(days=days - 1)
    sales = Sale.objects.filter(date__gte=since)
    revenue = sales.aggregate(t=Sum("total_amount"))["t"] or 0
    cogs = sales.aggregate(c=Sum(F("quantity") * F("product__purchase_price")))["c"] or 0
    expenses = Expense.objects.filter(date__gte=since).aggregate(t=Sum("amount"))["t"] or 0
    missing = Product.objects.filter(purchase_price=0).count()
    return {"days": days, "revenue": round(revenue, 2), "cost_of_goods": round(cogs, 2),
            "expenses": round(expenses, 2), "gross_profit": round(revenue - cogs, 2),
            "net_profit": round(revenue - cogs - expenses, 2),
            "warning": f"{missing} వస్తువులకు కొనుగోలు ధర లేదు, లాభం అంచనా మాత్రమే" if missing else ""}


def _suggest_qty(p) -> float:
    since = date.today() - timedelta(days=7)
    sold = Sale.objects.filter(product=p, date__gte=since).aggregate(q=Sum("quantity"))["q"] or 0
    avg = sold / 7
    target = max(avg * 7, p.low_stock_limit)       # కనీసం ఒక వారం సరిపడా
    return max(round(target - p.stock, 1), 0)


def smart_reorder_advice() -> list:
    """తక్కువ నిల్వ వస్తువులకు ఎంత కొనాలో అంచనా (గత 7 రోజుల అమ్మకాల ఆధారంగా). ఇది అంచనా మాత్రమే."""
    out = []
    for p in Product.objects.filter(stock__lt=F("low_stock_limit")).select_related("supplier"):
        qty = _suggest_qty(p)
        pred = predict_stockout(p.telugu_name)
        out.append({"product": p.telugu_name, "stock": p.stock, "unit": p.unit,
                    "days_left": pred.get("days_left"), "suggested_qty": qty,
                    "estimated_cost": round(qty * p.purchase_price, 2),
                    "supplier": p.supplier.name if p.supplier else None})
    return out


def mark_delivered(order_id: int) -> dict:
    """ఆమోదించిన order సరుకు వచ్చాక delivered గా గుర్తించి stock పెంచుతుంది."""
    try:
        o = ReorderOrder.objects.get(id=order_id)
    except ReorderOrder.DoesNotExist:
        return {"success": False, "message": "order దొరకలేదు"}
    if o.status != "approved":
        return {"success": False, "message": f"order స్థితి {o.status}, approved కావాలి"}
    for it in json.loads(o.items_json):
        p = _find(it["product"])
        if p:
            p.stock += it["quantity"]
            p.save()
            StockMovement.objects.create(product=p, change=it["quantity"],
                                         reason="purchase", ref=f"order{o.id}")
    o.status = "delivered"
    o.save()
    return {"success": True, "order_id": o.id, "status": "delivered"}


def expiry_alerts(days: int = 7) -> list:
    """త్వరలో గడువు ముగిసే వస్తువులు."""
    limit = date.today() + timedelta(days=days)
    rows = Product.objects.filter(expiry_date__isnull=False, expiry_date__lte=limit).order_by("expiry_date")
    return [{"product": p.telugu_name, "expiry": str(p.expiry_date),
             "days_left": (p.expiry_date - date.today()).days, "stock": p.stock} for p in rows]


def stock_history(product_name: str, limit: int = 10) -> list:
    """ఒక వస్తువు stock మార్పుల చరిత్ర."""
    p = _find(product_name)
    if not p:
        return []
    return [{"change": m.change, "reason": m.reason, "ref": m.ref,
             "time": m.created_at.strftime("%d %b %H:%M")}
            for m in StockMovement.objects.filter(product=p).order_by("-created_at")[:limit]]


def bill_history(limit: int = 10) -> list:
    """ఇటీవలి బిల్లులు."""
    return [{"bill_no": s.bill_no, "product": s.product.telugu_name, "quantity": s.quantity,
             "total": s.total_amount, "payment": s.payment_method, "date": str(s.date)}
            for s in Sale.objects.select_related("product").order_by("-id")[:limit]]