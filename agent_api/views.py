import json
from datetime import date, timedelta
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from . import tools, bill
from .agent import chat


def home(request):
    return render(request, "chat.html")


@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    data = json.loads(request.body)
    session_id = data.get("session_id", "default")
    message = data.get("message", "")
    try:
        reply = chat(session_id, message)
    except Exception as e:
        print("chat error:", e)
        if "429" in str(e):
            reply = "ప్రస్తుతం AI సేవ పరిమితి అయిపోయింది. కొద్దిసేపటి తర్వాత ప్రయత్నించండి."
        else:
            reply = "క్షమించండి, లోపం జరిగింది. మళ్ళీ ప్రయత్నించండి."
    return JsonResponse({"reply": reply})


def dashboard_api(request):
    from shop.models import Sale, Product, ReorderOrder
    n = int(request.GET.get("days", 7))
    n = n if n in (1, 7, 30) else 7
    days = []
    for i in range(n - 1, -1, -1):
        d = date.today() - timedelta(days=i)
        t = Sale.objects.filter(date=d).aggregate(t=Sum("total_amount"))["t"] or 0
        days.append({"day": d.strftime("%d %b"), "total": t})

    since = date.today() - timedelta(days=n)
    best = (Sale.objects.filter(date__gte=since)
            .values("product__telugu_name", "product__unit")
            .annotate(q=Sum("quantity"), amt=Sum("total_amount"))
            .order_by("-amt")[:5])
    week_total = sum(x["total"] for x in days)
    out_of_stock = list(Product.objects.filter(stock__lte=0).values_list("telugu_name", flat=True))
    credit = tools.pending_credit()
    return JsonResponse({
        "sales": tools.today_sales(),
        "low_stock": tools.low_stock_items(),
        "credit": credit,
        "week": days,
        "week_total": week_total,
        "best": [{"name": b["product__telugu_name"], "unit": b["product__unit"],
                  "qty": b["q"], "amt": b["amt"]} for b in best],
        "out_of_stock": out_of_stock,
        "credit_total": sum(c["balance_due"] for c in credit),
        "pending_orders": ReorderOrder.objects.filter(status="draft").count(),
        "profit": tools.profit_summary(n),
        "expiry": tools.expiry_alerts(7),
    })


def orders_api(request):
    from shop.models import ReorderOrder
    rows = []
    for o in ReorderOrder.objects.filter(status="draft").select_related("supplier"):
        rows.append({"id": o.id, "supplier": o.supplier.name,
                     "items": json.loads(o.items_json), "message": o.message})
    return JsonResponse({"orders": rows})


@csrf_exempt
def order_action(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    from shop.models import ReorderOrder
    data = json.loads(request.body)
    oid, action = data.get("id"), data.get("action")
    if action == "approve":
        return JsonResponse(tools.approve_reorder(int(oid)))
    try:
        o = ReorderOrder.objects.get(id=oid, status="draft")
        o.status = "cancelled"
        o.save()
        return JsonResponse({"success": True, "status": "cancelled"})
    except ReorderOrder.DoesNotExist:
        return JsonResponse({"success": False})


@csrf_exempt
def draft_api(request):
    return JsonResponse({"drafts": tools.draft_reorder()})


@csrf_exempt
def payment_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    data = json.loads(request.body)
    return JsonResponse(tools.record_payment(data["name"], float(data["amount"])))


@csrf_exempt
def scan_bill_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    f = request.FILES.get("image")
    if not f:
        return JsonResponse({"success": False, "message": "ఫోటో రాలేదు."})
    if f.size > 8 * 1024 * 1024:
        return JsonResponse({"success": False, "message": "ఫోటో చాలా పెద్దది (8MB లోపు కావాలి)."})
    if not (f.content_type or "").startswith("image/"):
        return JsonResponse({"success": False, "message": "ఇమేజ్ ఫైల్ మాత్రమే పంపండి."})
    return JsonResponse(bill.scan_bill(f.read(), f.content_type))


@csrf_exempt
def apply_bill_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    data = json.loads(request.body)
    return JsonResponse(bill.apply_bill(data.get("rows", [])))