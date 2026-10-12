import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from . import tools
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
        if "429" in str(e):
            reply = "ప్రస్తుతం AI సేవ పరిమితి అయిపోయింది. కొద్దిసేపటి తర్వాత ప్రయత్నించండి."
        else:
            reply = f"క్షమించండి, లోపం జరిగింది: {e}"
    return JsonResponse({"reply": reply})


def dashboard_api(request):
    return JsonResponse({
        "sales": tools.today_sales(),
        "low_stock": tools.low_stock_items(),
        "credit": tools.pending_credit(),
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