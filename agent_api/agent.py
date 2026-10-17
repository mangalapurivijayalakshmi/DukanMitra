import logging
import math
import os
import threading

from dotenv import load_dotenv
from google import genai
from google.genai import types

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from shop.models import Customer, PendingAction, Product

from . import festival, tools


load_dotenv()

logger = logging.getLogger(__name__)


MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite",
)


SYSTEM_PROMPT = """
నువ్వు DukanMitra, కిరాణా దుకాణదారుల కోసం AI సహాయకుడివి.

భాష:
- సాధారణంగా సరళమైన తెలుగులో చిన్నగా సమాధానం ఇవ్వు.
- యజమాని Englishలో సమాధానం అడిగితే Englishలో చెప్పు.

Business questions:
- స్టాక్, ధరలు, అమ్మకాలు, బాకీలు, లాభం కోసం tools వాడు.
- Tool data లేకుండా business numbers ఊహించకు.
- Revenueని profit అనకు.
- Profit warning ఉంటే చెప్పు.
- Forecasts, reorder advice, festival advice అంచనాలు మాత్రమే.
- Supplierకి WhatsApp message/order పంపినట్టు చెప్పవద్దు.

Conversation:
- ఈ versionలో గత messages గుర్తుండవు.
- అవసరమైన వివరాలు లేకపోతే పూర్తి వివరాలతో మళ్లీ అడగమని చెప్పు.
- గత message ఆధారంగా transaction details ఊహించకు.

Sale workflow:
- అమ్మకం నమోదు చేయమంటే propose_sale tool మాత్రమే వాడు.
- ఒక్క requestలో ఒక్క sale proposal మాత్రమే support చేస్తాం.
- Multiple items ఉంటే ఒక్కొక్కటిగా ఇవ్వమని చెప్పు.
- propose_sale actual sale నమోదు చేయదు.
- అది owner review కోసం pending proposal మాత్రమే తయారు చేస్తుంది.
- Credit saleకి payment_method="credit", customer_name ఇవ్వాలి.
- Cash లేదా UPI payment స్పష్టంగా తెలియకపోతే clarification అడుగు.
- Customer పేరు ఏ scriptలో ఇచ్చినా అది అలాగే toolకి ఇవ్వవచ్చు.
- Product/customer ambiguous అయితే పూర్తి పేరు అడుగు.
- Proposal success అంటే sale recorded అని కాదు.
- Stock తగ్గిందని లేదా customer బాకీ పెరిగిందని చెప్పవద్దు.
- Proposal తర్వాత పైన UI review cardలో Confirm sale లేదా Cancel ఎంచుకోమని చెప్పు.
- Actual execution server confirmation endpoint ద్వారా జరుగుతుంది.
- Chatలో "అవును" అన్నంత మాత్రాన actual sale execute చేయవద్దు.
- "అవును", "confirm", "cancel" మాత్రమే ఉన్న messageతో కొత్త proposal create చేయవద్దు.
- ఇప్పటికే జరిగిన saleని reverse చేశానని చెప్పవద్దు.

Other write actions:
- Payment, expense, reorder approval, delivery chat tools ఈ versionలో లేవు.
- ఆ actions పూర్తయ్యాయని చెప్పవద్దు.
- Reorder advice కోసం smart_reorder_advice వాడు.
"""


# Explicit aliases for the current demo dataset.
# This is not a general transliteration system.
CUSTOMER_NAME_ALIASES = {
    "రమేష్": "Ramesh",
    "రమేశ్": "Ramesh",
    "లక్ష్మి": "Lakshmi",
    "లక్ష్మీ": "Lakshmi",
    "సురేష్": "Suresh",
    "సురేశ్": "Suresh",
    "పద్మ": "Padma",
}


# No direct business-write functions are exposed to the model.
READ_ONLY_TOOLS = [
    tools.get_stock,
    tools.get_price,
    tools.low_stock_items,
    tools.today_sales,
    tools.pending_credit,
    tools.predict_stockout,
    tools.daily_summary,
    tools.customer_credit,
    tools.best_sellers,
    tools.profit_summary,
    tools.smart_reorder_advice,
    tools.expiry_alerts,
    tools.stock_history,
    tools.bill_history,
    festival.festival_advice,
]


_client = None

# Temporary process-local serialization.
# This does not replace database concurrency controls.
_chat_lock = threading.Lock()


def _get_client():
    """
    Return the shared Gemini client.

    bill.py also imports this function.
    """
    global _client

    if _client is None:
        _client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"]
        )

    return _client


def _resolve_unique(model, name, fields):
    """
    Prefer an exact match.

    Accept a partial match only when exactly one record matches.
    """
    if not isinstance(name, str) or not name.strip():
        return None, {
            "success": False,
            "message": "పేరు ఖాళీగా ఉండకూడదు.",
        }

    name = name.strip()

    if model is Customer:
        name = CUSTOMER_NAME_ALIASES.get(name, name)

    exact_query = Q()

    for field in fields:
        exact_query |= Q(
            **{f"{field}__iexact": name}
        )

    matches = list(
        model.objects.filter(exact_query)
        .order_by("pk")[:6]
    )

    if not matches:
        partial_query = Q()

        for field in fields:
            partial_query |= Q(
                **{f"{field}__icontains": name}
            )

        matches = list(
            model.objects.filter(partial_query)
            .order_by("pk")[:6]
        )

    if not matches:
        return None, {
            "success": False,
            "message": f"'{name}' దొరకలేదు.",
        }

    if len(matches) != 1:
        options = []

        for item in matches:
            if isinstance(item, Product):
                options.append(
                    f"{item.telugu_name} ({item.name})"
                )
            else:
                options.append(item.name)

        return None, {
            "success": False,
            "needs_clarification": True,
            "message": (
                "ఒకటి కంటే ఎక్కువ matches ఉన్నాయి. "
                "పూర్తి పేరు చెప్పండి."
            ),
            "options": options,
        }

    return matches[0], None


def _create_sale_proposal(
    owner_session_key,
    product_name,
    quantity,
    payment_method,
    customer_name,
):
    """
    Validate and store a sale proposal.

    Does not create Sale/StockMovement records.
    Does not change product stock or customer balance.
    """
    if not owner_session_key:
        return {
            "success": False,
            "message": "Server session అందుబాటులో లేదు.",
        }

    if isinstance(quantity, bool):
        return {
            "success": False,
            "message": "పరిమాణం సరిగా లేదు.",
        }

    try:
        quantity = float(quantity)

    except (TypeError, ValueError, OverflowError):
        return {
            "success": False,
            "message": "పరిమాణం సంఖ్యగా ఇవ్వాలి.",
        }

    if not math.isfinite(quantity) or quantity <= 0:
        return {
            "success": False,
            "message": (
                "పరిమాణం సున్నా కంటే ఎక్కువగా, "
                "finite numberగా ఉండాలి."
            ),
        }

    if not isinstance(payment_method, str):
        return {
            "success": False,
            "message": "Payment method సరిగా లేదు.",
        }

    method = payment_method.strip().lower()

    if method not in {"cash", "upi", "credit"}:
        return {
            "success": False,
            "message": (
                "Payment method cash, upi లేదా credit కావాలి."
            ),
        }

    product, error = _resolve_unique(
        Product,
        product_name,
        ("telugu_name", "name"),
    )

    if error:
        return error

    stock = float(product.stock)
    price = float(product.price)

    if (
        not math.isfinite(stock)
        or not math.isfinite(price)
        or stock < 0
        or price < 0
    ):
        return {
            "success": False,
            "message": (
                "Product stock/price వివరాలు సరిచూడాలి."
            ),
        }

    if stock < quantity:
        return {
            "success": False,
            "message": (
                f"నిల్వ సరిపోదు. ఉన్నది "
                f"{stock} {product.unit}."
            ),
        }

    customer = None
    balance = None

    if method == "credit":
        customer, error = _resolve_unique(
            Customer,
            customer_name,
            ("name",),
        )

        if error:
            return error

        balance = float(customer.balance_due)

        if not math.isfinite(balance) or balance < 0:
            return {
                "success": False,
                "message": (
                    "Customer balance వివరాలు సరిచూడాలి."
                ),
            }

    total = round(quantity * price, 2)

    if not math.isfinite(total):
        return {
            "success": False,
            "message": "Sale total సరిగా లేదు.",
        }

    arguments = {
        "product_id": product.pk,
        "customer_id": customer.pk if customer else None,
        "quantity": quantity,
        "payment_method": method,
        "unit_price": price,
        "expected_total": total,
    }

    preview = {
        "product": product.telugu_name,
        "quantity": quantity,
        "unit": product.unit,
        "unit_price": price,
        "total": total,
        "payment_method": method,
        "stock_before": stock,
        "stock_after": stock - quantity,
        "customer": customer.name if customer else None,
    }

    if customer:
        dues_after = round(balance + total, 2)

        if not math.isfinite(dues_after):
            return {
                "success": False,
                "message": "Customer balance total సరిగా లేదు.",
            }

        preview["dues_before"] = balance
        preview["dues_after"] = dues_after

    now = timezone.now()

    with transaction.atomic():
        PendingAction.objects.filter(
            session_key=owner_session_key,
            action_type=PendingAction.ActionType.RECORD_SALE,
            status=PendingAction.Status.PENDING,
            expires_at__lte=now,
        ).update(
            status=PendingAction.Status.EXPIRED
        )

        existing = (
            PendingAction.objects.filter(
                session_key=owner_session_key,
                action_type=PendingAction.ActionType.RECORD_SALE,
                status=PendingAction.Status.PENDING,
                expires_at__gt=now,
            )
            .order_by("-created_at")
            .first()
        )

        if existing:
            if (
                existing.arguments == arguments
                and existing.preview == preview
            ):
                action = existing

            else:
                return {
                    "success": False,
                    "message": (
                        "ఈ browser sessionలో ఇప్పటికే ఒక "
                        "pending sale proposal ఉంది. "
                        "పైన ఉన్న review cardలో దాన్ని "
                        "Confirm లేదా Cancel చేయండి. "
                        "తర్వాత కొత్త sale అడగండి."
                    ),
                    "pending_action_id": str(existing.pk),
                    "expires_at": (
                        existing.expires_at.isoformat()
                    ),
                }

        else:
            action = PendingAction.objects.create(
                session_key=owner_session_key,
                action_type=(
                    PendingAction.ActionType.RECORD_SALE
                ),
                arguments=arguments,
                preview=preview,
            )

    return {
        "success": True,
        "status": "pending",
        "action_id": str(action.pk),
        "expires_at": action.expires_at.isoformat(),
        "preview": preview,
        "message": (
            "Sale proposal మాత్రమే సిద్ధమైంది. "
            "Stock/బాకీ మార్చలేదు. "
            "UI review cardలో Confirm sale లేదా Cancel ఎంచుకోండి."
        ),
    }


def _format_sale_proposal(result):
    preview = result["preview"]

    lines = [
        "🧾 Sale proposal — ఇంకా నమోదు కాలేదు",
        "",
        f"వస్తువు: {preview['product']}",
        (
            f"పరిమాణం: {preview['quantity']} "
            f"{preview['unit']}"
        ),
        f"యూనిట్ ధర: ₹{preview['unit_price']:.2f}",
        f"మొత్తం: ₹{preview['total']:.2f}",
        f"Payment: {preview['payment_method']}",
        "",
        (
            "ఆమోదిస్తే stock: "
            f"{preview['stock_before']} → "
            f"{preview['stock_after']} {preview['unit']}"
        ),
    ]

    if preview.get("customer"):
        lines.extend([
            f"కస్టమర్: {preview['customer']}",
            (
                "ఆమోదిస్తే బాకీ: "
                f"₹{preview['dues_before']:.2f} → "
                f"₹{preview['dues_after']:.2f}"
            ),
        ])

    lines.extend([
        "",
        f"Proposal ID: {result['action_id']}",
        "",
        "Stock/బాకీ ఇంకా మార్చలేదు.",
        (
            "పైన ఉన్న review cardలో "
            "Confirm sale లేదా Cancel ఎంచుకోండి."
        ),
    ])

    return "\n".join(lines)


def _format_proposal_error(result):
    lines = [
        result.get(
            "message",
            "Sale proposal సిద్ధం కాలేదు.",
        )
    ]

    options = result.get("options")

    if isinstance(options, list) and options:
        lines.append(
            "Matches: " +
            ", ".join(str(item) for item in options)
        )

    return "\n".join(lines)


def chat(
    session_id: str,
    message: str,
    owner_session_key: str = "",
) -> str:
    """
    Answer one self-contained request.

    session_id is retained for compatibility with views.py.
    Proposal ownership uses the server-provided session key.
    This version does not retain conversation history.
    """
    if not owner_session_key:
        return (
            "Server session అందుబాటులో లేదు. "
            "Chat viewలో session binding connect చేయాలి."
        )

    if not isinstance(message, str) or not message.strip():
        return "మీ ప్రశ్నను నమోదు చేయండి."

    message = message.strip()

    # These short responses must not trigger another proposal.
    confirmation_only_messages = {
        "అవును",
        "ఓకే",
        "సరే",
        "ఒప్పుకుంటున్నాను",
        "ఆమోదించు",
        "రద్దు",
        "రద్దు చేయి",
        "yes",
        "ok",
        "okay",
        "confirm",
        "confirm sale",
        "cancel",
    }

    normalized_message = message.casefold().strip(
        " \t\r\n.!?।"
    )

    if normalized_message in confirmation_only_messages:
        return (
            "Chat messageతో sale execute చేయను. "
            "Pending proposal ఉంటే పైన ఉన్న review cardలో "
            "Confirm sale లేదా Cancel ఎంచుకోండి. "
            "Card లేకపోతే పూర్తి sale వివరాలతో కొత్తగా అడగండి."
        )

    proposal_results = []

    def propose_sale(
        product_name: str,
        quantity: float,
        payment_method: str,
        customer_name: str = "",
    ) -> dict:
        """
        Prepare one sale proposal for owner review.

        Does not record a sale or change stock/customer dues.
        payment_method must be cash, upi, or credit.
        customer_name is required for credit.
        """
        successful = [
            item
            for item in proposal_results
            if item.get("success") is True
        ]

        if successful:
            return {
                "success": False,
                "message": (
                    "ఈ requestలో ఇప్పటికే ఒక proposal సిద్ధమైంది. "
                    "UI review cardలో సరిచూడండి."
                ),
                "pending_action_id": (
                    successful[-1]["action_id"]
                ),
            }

        result = _create_sale_proposal(
            owner_session_key=owner_session_key,
            product_name=product_name,
            quantity=quantity,
            payment_method=payment_method,
            customer_name=customer_name,
        )

        proposal_results.append(result)
        return result

    try:
        with _chat_lock:
            conversation = _get_client().chats.create(
                model=MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=READ_ONLY_TOOLS + [propose_sale],
                ),
            )

            response = conversation.send_message(message)

    except Exception:
        successful = [
            item
            for item in proposal_results
            if item.get("success") is True
        ]

        if successful:
            logger.exception(
                "Agent response failed after proposal creation"
            )

            return _format_sale_proposal(
                successful[-1]
            )

        # views.py logs and handles the original exception.
        raise

    successful = [
        item
        for item in proposal_results
        if item.get("success") is True
    ]

    if successful:
        return _format_sale_proposal(
            successful[-1]
        )

    if proposal_results:
        return _format_proposal_error(
            proposal_results[-1]
        )

    reply = getattr(response, "text", None)

    if isinstance(reply, str) and reply.strip():
        return reply.strip()

    return "సమాధానం పొందలేకపోయాను. మళ్లీ ప్రయత్నించండి."