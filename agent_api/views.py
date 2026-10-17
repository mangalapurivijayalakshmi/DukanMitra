import json
import logging
import struct
import zlib

from datetime import date, timedelta
from functools import lru_cache

from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import (
    csrf_exempt,
    csrf_protect,
    ensure_csrf_cookie,
)
from django.db.models import Sum

from . import tools, bill, festival, approvals
from .agent import chat

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def home(request):
    return render(request, "chat.html")

@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "message": "సరైన JSON data పంపండి."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"success": False, "message": "JSON object అవసరం."}, status=400)

    session_id = data.get("session_id")
    message = data.get("message")

    if not isinstance(session_id, str) or not session_id.strip():
        return JsonResponse({"success": False, "message": "Session ID అవసరం."}, status=400)
    if not isinstance(message, str) or not message.strip():
        return JsonResponse({"success": False, "message": "మీ ప్రశ్నను నమోదు చేయండి."}, status=400)
    try:
        if not request.session.session_key:
            request.session.create()

        reply = chat(
            session_id=session_id.strip(),
            message=message.strip(),
            owner_session_key=request.session.session_key,
        )
    except Exception as error:
        logger.exception("Chat request failed")
        if "429" in str(error):
            reply = "ప్రస్తుతం AI సేవ పరిమితి అయిపోయింది. కొద్దిసేపటి తర్వాత ప్రయత్నించండి."
        else:
            reply = "క్షమించండి, లోపం జరిగింది. మళ్ళీ ప్రయత్నించండి."
        return JsonResponse({"success": False, "message": reply, "reply": reply}, status=503)

    if not isinstance(reply, str) or not reply.strip():
        return JsonResponse({"success": False, "message": "AI నుంచి సరైన సమాధానం రాలేదు."}, status=502)

    return JsonResponse({"success": True, "reply": reply})

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
        "festival": festival.festival_advice(),
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


# ---------------- 📱 PWA ----------------

def manifest(request):
    return JsonResponse({
        "name": "DukanMitra - తెలుగు AI దుకాణ సహాయకుడు",
        "short_name": "DukanMitra",
        "description": "కిరాణా దుకాణదారుల కోసం తెలుగు AI సహాయకుడు",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f1f8f3",
        "theme_color": "#1b8a4b",
        "lang": "te",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }, content_type="application/manifest+json")


SW_JS = """
const CACHE = "dukanmitra-v1";
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(["/", "/manifest.json"])));
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  const isApi = url.pathname.startsWith("/api/");
  const cacheableApi = url.pathname.startsWith("/api/dashboard") || url.pathname.startsWith("/api/orders");
  if (isApi && !cacheableApi) return;
  e.respondWith(
    fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req))
  );
});
"""

def pending_actions_api(request):
    if request.method != "GET":
        response = JsonResponse(
            {
                "success": False,
                "message": "GET only",
            },
            status=405,
        )
        response["Allow"] = "GET"
        response["Cache-Control"] = "no-store"
        return response

    result = approvals.list_pending_actions(
        owner_session_key=request.session.session_key
    )

    http_status = result.pop("http_status", 200)

    response = JsonResponse(
        result,
        status=http_status,
    )

    response["Cache-Control"] = "no-store"
    return response


@csrf_protect
def pending_action_api(request):
    if request.method != "POST":
        response = JsonResponse(
            {
                "success": False,
                "message": "POST only",
            },
            status=405,
        )
        response["Allow"] = "POST"
        response["Cache-Control"] = "no-store"
        return response

    owner_session_key = request.session.session_key

    if not owner_session_key:
        response = JsonResponse(
            {
                "success": False,
                "message": (
                    "Server session అందుబాటులో లేదు. "
                    "Page refresh చేసి కొత్త proposal తీసుకోండి."
                ),
            },
            status=403,
        )
        response["Cache-Control"] = "no-store"
        return response

    try:
        data = json.loads(request.body)

    except (json.JSONDecodeError, UnicodeDecodeError):
        response = JsonResponse(
            {
                "success": False,
                "message": "సరైన JSON data పంపండి.",
            },
            status=400,
        )
        response["Cache-Control"] = "no-store"
        return response

    if not isinstance(data, dict):
        response = JsonResponse(
            {
                "success": False,
                "message": "JSON object అవసరం.",
            },
            status=400,
        )
        response["Cache-Control"] = "no-store"
        return response

    action_id = data.get("id")
    action = data.get("action")

    if (
        not isinstance(action_id, str)
        or not action_id.strip()
        or not isinstance(action, str)
        or action not in {"confirm", "cancel"}
    ):
        response = JsonResponse(
            {
                "success": False,
                "message": (
                    "Valid proposal ID మరియు "
                    "confirm/cancel action అవసరం."
                ),
            },
            status=400,
        )
        response["Cache-Control"] = "no-store"
        return response

    result = approvals.process_pending_action(
        owner_session_key=owner_session_key,
        action_id=action_id.strip(),
        action=action,
    )

    http_status = result.pop("http_status", 200)

    response = JsonResponse(
        result,
        status=http_status,
    )

    response["Cache-Control"] = "no-store"
    return response

def service_worker(request):
    resp = HttpResponse(SW_JS, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


@lru_cache(maxsize=4)
def _icon_png(size):
    bg, fg = (27, 138, 75), (255, 255, 255)
    c, r_out, r_in = size / 2, size * 0.34, size * 0.20
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
            raw.extend(fg if r_in <= d <= r_out else bg)

    def chunk(t, data):
        return (struct.pack(">I", len(data)) + t + data +
                struct.pack(">I", zlib.crc32(t + data) & 0xffffffff))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def icon(request, size):
    if size not in (192, 512):
        raise Http404
    return HttpResponse(_icon_png(size), content_type="image/png")
