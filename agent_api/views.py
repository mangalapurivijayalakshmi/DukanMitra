import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .agent import chat
from . import tools

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
        reply = f"క్షమించండి, లోపం జరిగింది: {e}"
    return JsonResponse({"reply": reply})

def dashboard_api(request):
    return JsonResponse({
        "sales": tools.today_sales(),
        "low_stock": tools.low_stock_items(),
        "credit": tools.pending_credit(),
    })