import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from . import tools
from .agent import chat
from datetime import date, timedelta
from django.db.models import Sum


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
        if "429" in str(e):
            reply = "ప్రస్తుతం AI సేవ పరిమితి అయిపోయింది. కొద్దిసేపటి తర్వాత ప్రయత్నించండి."
        else:
            reply = f"క్షమించండి, లోపం జరిగింది: {e}"
    return JsonResponse({"reply": reply})


def dashboard_api(request):
    from shop.models import Sale, Product
    n = int(request.GET.get("days", 7))
    n = n if n in (1, 7, 30) else 7
    days = []
    for i in range(n-1, -1, -1):
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
    sales = tools.today_sales()
    return JsonResponse({
        "sales": sales,
        "low_stock": tools.low_stock_items(),
        "credit": tools.pending_credit(),
        "week": days,
        "week_total": week_total,
        "best": [{"name": b["product__telugu_name"], "unit": b["product__unit"],
                  "qty": b["q"], "amt": b["amt"]} for b in best],
        "out_of_stock": out_of_stock,
        "credit_total": sum(c["balance_due"] for c in tools.pending_credit()),
        "pending_orders": __import__("shop.models", fromlist=["ReorderOrder"]).ReorderOrder.objects.filter(status="draft").count(),
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
    drafts = tools.draft_reorder()
    return JsonResponse({"drafts": drafts})