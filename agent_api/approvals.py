import logging
import math
import uuid

from django.db import DatabaseError, transaction
from django.db.models import F
from django.utils import timezone

from shop.models import (
    Customer,
    PendingAction,
    Product,
    Sale,
    StockMovement,
)


logger = logging.getLogger(__name__)


class InvalidSaleProposal(Exception):
    """The stored proposal is invalid or no longer matches current data."""


class ConcurrentSaleChange(Exception):
    """A conditional business update did not match the reviewed data."""


def _error(message, http_status=400, **extra):
    return {
        "success": False,
        "message": message,
        "http_status": http_status,
        **extra,
    }


def _success(message, **extra):
    return {
        "success": True,
        "message": message,
        "http_status": 200,
        **extra,
    }


def _finite_number(value, label):
    if isinstance(value, bool) or value is None:
        raise InvalidSaleProposal(
            f"{label} సరిగా లేదు."
        )

    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        raise InvalidSaleProposal(
            f"{label} సరిగా లేదు."
        )

    if not math.isfinite(result):
        raise InvalidSaleProposal(
            f"{label} finite number కావాలి."
        )

    return result


def _positive_id(value, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise InvalidSaleProposal(
            f"{label} సరిగా లేదు."
        )

    return value


def _same_number(left, right):
    return math.isclose(
        left,
        right,
        rel_tol=0,
        abs_tol=0.000000001,
    )


def _validate_sale(action):
    """
    Validate stored arguments and the reviewed preview.

    This function must be called inside the execution transaction.
    It does not perform business writes.
    """
    arguments = action.arguments
    preview = action.preview

    if not isinstance(arguments, dict):
        raise InvalidSaleProposal(
            "Proposal arguments సరిగా లేవు."
        )

    if not isinstance(preview, dict):
        raise InvalidSaleProposal(
            "Proposal preview సరిగా లేదు."
        )

    product_id = _positive_id(
        arguments.get("product_id"),
        "Product ID",
    )

    quantity = _finite_number(
        arguments.get("quantity"),
        "పరిమాణం",
    )

    unit_price = _finite_number(
        arguments.get("unit_price"),
        "యూనిట్ ధర",
    )

    expected_total = _finite_number(
        arguments.get("expected_total"),
        "Sale total",
    )

    method = arguments.get("payment_method")

    if method not in {"cash", "upi", "credit"}:
        raise InvalidSaleProposal(
            "Payment method సరిగా లేదు."
        )

    if quantity <= 0 or unit_price < 0:
        raise InvalidSaleProposal(
            "పరిమాణం లేదా ధర సరిగా లేదు."
        )

    total = round(quantity * unit_price, 2)

    if not math.isfinite(total):
        raise InvalidSaleProposal(
            "Sale total సరిగా లేదు."
        )

    if expected_total != total:
        raise InvalidSaleProposal(
            "Proposal total సరిపోలడం లేదు."
        )

    try:
        product = (
            Product.objects.select_for_update()
            .get(pk=product_id)
        )
    except Product.DoesNotExist:
        raise InvalidSaleProposal(
            "Proposalలోని వస్తువు ఇప్పుడు అందుబాటులో లేదు."
        )

    stock = _finite_number(
        product.stock,
        "ప్రస్తుత stock",
    )

    current_price = _finite_number(
        product.price,
        "ప్రస్తుత ధర",
    )

    stock_before = _finite_number(
        preview.get("stock_before"),
        "Preview stock",
    )

    stock_after = _finite_number(
        preview.get("stock_after"),
        "Preview remaining stock",
    )

    preview_quantity = _finite_number(
        preview.get("quantity"),
        "Preview quantity",
    )

    preview_price = _finite_number(
        preview.get("unit_price"),
        "Preview unit price",
    )

    preview_total = _finite_number(
        preview.get("total"),
        "Preview total",
    )

    if (
        preview.get("product") != product.telugu_name
        or preview.get("unit") != product.unit
        or preview.get("payment_method") != method
        or preview_quantity != quantity
        or preview_price != unit_price
        or preview_total != total
    ):
        raise InvalidSaleProposal(
            "Proposal వివరాలు సరిపోలడం లేదు. "
            "కొత్త proposal తీసుకుని review చేయండి."
        )

    if current_price != unit_price:
        raise InvalidSaleProposal(
            "వస్తువు ధర మారింది. కొత్త proposal అవసరం."
        )

    if stock != stock_before:
        raise InvalidSaleProposal(
            "Stock మారింది. కొత్త proposal అవసరం."
        )

    if stock < quantity:
        raise InvalidSaleProposal(
            "ప్రస్తుతం stock సరిపోదు."
        )

    if not _same_number(
        stock_after,
        stock - quantity,
    ):
        raise InvalidSaleProposal(
            "Preview stock calculation సరిగా లేదు."
        )

    customer = None
    balance_before = None

    if method == "credit":
        customer_id = _positive_id(
            arguments.get("customer_id"),
            "Customer ID",
        )

        try:
            customer = (
                Customer.objects.select_for_update()
                .get(pk=customer_id)
            )
        except Customer.DoesNotExist:
            raise InvalidSaleProposal(
                "Proposalలోని customer అందుబాటులో లేరు."
            )

        balance_before = _finite_number(
            customer.balance_due,
            "ప్రస్తుత బాకీ",
        )

        reviewed_balance = _finite_number(
            preview.get("dues_before"),
            "Preview బాకీ",
        )

        reviewed_balance_after = _finite_number(
            preview.get("dues_after"),
            "Preview remaining balance",
        )

        if balance_before < 0:
            raise InvalidSaleProposal(
                "Customer balance సరిచూడాలి."
            )

        if preview.get("customer") != customer.name:
            raise InvalidSaleProposal(
                "Customer వివరాలు మారాయి. "
                "కొత్త proposal అవసరం."
            )

        if balance_before != reviewed_balance:
            raise InvalidSaleProposal(
                "Customer బాకీ మారింది. "
                "కొత్త proposal అవసరం."
            )

        balance_after = round(
            balance_before + total,
            2,
        )

        if (
            not math.isfinite(balance_after)
            or not _same_number(
                reviewed_balance_after,
                balance_after,
            )
        ):
            raise InvalidSaleProposal(
                "Preview బాకీ calculation సరిగా లేదు."
            )

    else:
        if (
            arguments.get("customer_id") is not None
            or preview.get("customer") is not None
        ):
            raise InvalidSaleProposal(
                "Cash/UPI proposal customer details సరిగా లేవు."
            )

    return {
        "product": product,
        "customer": customer,
        "quantity": quantity,
        "unit_price": unit_price,
        "total": total,
        "payment_method": method,
        "stock_before": stock,
        "balance_before": balance_before,
    }


def _execute_sale(action, validated):
    """
    Execute a validated sale inside the caller's transaction.

    Do not call the old name-based tools.record_sale() here.
    Use the IDs and values from the stored, reviewed proposal.
    """
    product = validated["product"]
    customer = validated["customer"]
    quantity = validated["quantity"]
    unit_price = validated["unit_price"]
    total = validated["total"]
    method = validated["payment_method"]
    stock_before = validated["stock_before"]
    balance_before = validated["balance_before"]

    # Reject rather than overwrite an unexpected stock/price change.
    stock_updated = Product.objects.filter(
        pk=product.pk,
        stock=stock_before,
        stock__gte=quantity,
        price=unit_price,
        telugu_name=product.telugu_name,
        unit=product.unit,
    ).update(
        stock=F("stock") - quantity
    )

    if stock_updated != 1:
        raise ConcurrentSaleChange(
            "Stock/price మారింది. కొత్త proposal అవసరం."
        )

    if customer:
        customer_updates = {
            "balance_due": F("balance_due") + total,
        }

        if (
            balance_before <= 0
            or customer.credit_since is None
        ):
            customer_updates["credit_since"] = (
                timezone.localdate()
            )

        customer_updated = Customer.objects.filter(
            pk=customer.pk,
            name=customer.name,
            balance_due=balance_before,
        ).update(
            **customer_updates
        )

        if customer_updated != 1:
            raise ConcurrentSaleChange(
                "Customer బాకీ మారింది. "
                "కొత్త proposal అవసరం."
            )

    sale = Sale.objects.create(
        product=product,
        quantity=quantity,
        total_amount=total,
        date=timezone.localdate(),
        payment_method=method,
    )

    sale.bill_no = f"B{sale.pk:05d}"
    sale.save(update_fields=["bill_no"])

    StockMovement.objects.create(
        product=product,
        change=-quantity,
        reason="sale",
        ref=sale.bill_no,
    )

    product.refresh_from_db(fields=["stock"])

    result = {
        "bill_no": sale.bill_no,
        "sale_id": sale.pk,
        "product_id": product.pk,
        "product": product.telugu_name,
        "quantity": quantity,
        "unit": product.unit,
        "total": total,
        "payment_method": method,
        "stock_left": product.stock,
    }

    if customer:
        customer.refresh_from_db(
            fields=["balance_due"]
        )

        result.update({
            "customer_id": customer.pk,
            "customer": customer.name,
            "balance_left": customer.balance_due,
        })

    action.status = PendingAction.Status.EXECUTED
    action.executed_at = timezone.now()
    action.result = result

    action.save(
        update_fields=[
            "status",
            "executed_at",
            "result",
        ]
    )

    return _success(
        "అమ్మకం నమోదు అయింది.",
        action_id=str(action.pk),
        status=action.status,
        already_executed=False,
        result=result,
    )


def list_pending_actions(owner_session_key):
    """
    Return unexpired sale proposals belonging to this server session.

    owner_session_key must come from request.session.session_key.
    Do not accept it from request JSON.
    """
    if not owner_session_key:
        return {
            "success": True,
            "http_status": 200,
            "actions": [],
        }

    actions = PendingAction.objects.filter(
        session_key=owner_session_key,
        action_type=PendingAction.ActionType.RECORD_SALE,
        status=PendingAction.Status.PENDING,
        expires_at__gt=timezone.now(),
    ).order_by("-created_at")

    return {
        "success": True,
        "http_status": 200,
        "actions": [
            {
                "id": str(action.pk),
                "action_type": action.action_type,
                "status": action.status,
                "preview": action.preview,
                "created_at": action.created_at.isoformat(),
                "expires_at": action.expires_at.isoformat(),
            }
            for action in actions
        ],
    }


def process_pending_action(
    owner_session_key,
    action_id,
    action,
):
    """
    Confirm or cancel one stored sale proposal.

    Returns a dictionary containing http_status for the API view.
    The API view must enforce POST and CSRF protection.
    """
    if not owner_session_key:
        return _error(
            "Server session అవసరం.",
            http_status=403,
        )

    if action not in {"confirm", "cancel"}:
        return _error(
            "Action confirm లేదా cancel కావాలి."
        )

    try:
        proposal_id = uuid.UUID(str(action_id))
    except (ValueError, TypeError, AttributeError):
        return _error(
            "Proposal ID సరిగా లేదు."
        )

    try:
        with transaction.atomic():
            now = timezone.now()

            # The first DB statement is a conditional write.
            # Only a pending, unexpired sale can be claimed.
            claimed = PendingAction.objects.filter(
                pk=proposal_id,
                session_key=owner_session_key,
                action_type=PendingAction.ActionType.RECORD_SALE,
                status=PendingAction.Status.PENDING,
                expires_at__gt=now,
            ).update(
                status=PendingAction.Status.EXECUTING
            )

            proposal = PendingAction.objects.filter(
                pk=proposal_id,
                session_key=owner_session_key,
                action_type=PendingAction.ActionType.RECORD_SALE,
            ).first()

            if proposal is None:
                return _error(
                    "ఈ sessionకి proposal అందుబాటులో లేదు.",
                    http_status=404,
                )

            if claimed != 1:
                if (
                    proposal.status
                    == PendingAction.Status.EXECUTED
                ):
                    if action == "confirm":
                        return _success(
                            "ఈ sale ఇప్పటికే నమోదు అయింది. "
                            "మళ్లీ నమోదు చేయలేదు.",
                            action_id=str(proposal.pk),
                            status=proposal.status,
                            already_executed=True,
                            result=proposal.result,
                        )

                    return _error(
                        "నమోదైన saleని ఈ endpointతో "
                        "cancel చేయలేరు.",
                        http_status=409,
                        status=proposal.status,
                    )

                if (
                    proposal.status
                    == PendingAction.Status.CANCELLED
                    and action == "cancel"
                ):
                    return _success(
                        "Proposal ఇప్పటికే cancel అయింది.",
                        action_id=str(proposal.pk),
                        status=proposal.status,
                    )

                if (
                    proposal.status
                    == PendingAction.Status.PENDING
                    and proposal.expires_at <= now
                ):
                    PendingAction.objects.filter(
                        pk=proposal.pk,
                        session_key=owner_session_key,
                        status=PendingAction.Status.PENDING,
                        expires_at__lte=now,
                    ).update(
                        status=PendingAction.Status.EXPIRED
                    )

                    return _error(
                        "Proposal గడువు ముగిసింది. "
                        "కొత్త proposal తీసుకోండి.",
                        http_status=409,
                        status=PendingAction.Status.EXPIRED,
                    )

                return _error(
                    "ఈ proposal ప్రస్తుతం execute చేయలేరు.",
                    http_status=409,
                    status=proposal.status,
                )

            if action == "cancel":
                proposal.status = (
                    PendingAction.Status.CANCELLED
                )

                proposal.result = {
                    "message": "Owner cancelled the proposal."
                }

                proposal.save(
                    update_fields=["status", "result"]
                )

                return _success(
                    "Proposal cancel అయింది. "
                    "Stock/బాకీ మార్చలేదు.",
                    action_id=str(proposal.pk),
                    status=proposal.status,
                )

            try:
                validated = _validate_sale(proposal)

            except InvalidSaleProposal as error:
                # No business writes have happened at this point.
                proposal.status = PendingAction.Status.FAILED
                proposal.result = {
                    "message": str(error)
                }

                proposal.save(
                    update_fields=["status", "result"]
                )

                return _error(
                    str(error),
                    http_status=409,
                    status=proposal.status,
                )

            return _execute_sale(
                proposal,
                validated,
            )

    except ConcurrentSaleChange as error:
        # The atomic block rolls back all business writes and the claim.
        return _error(
            str(error) +
            " ప్రస్తుత proposalని cancel చేసి మళ్లీ అడగండి.",
            http_status=409,
        )

    except DatabaseError:
        logger.exception(
            "Database error while processing pending sale"
        )

        return _error(
            "Database confirmation పొందలేకపోయాను. "
            "మళ్లీ Confirm చేసే ముందు proposal/bill status "
            "తనిఖీ చేయండి.",
            http_status=503,
        )

    except Exception:
        logger.exception(
            "Unexpected error while processing pending sale"
        )

        return _error(
            "Sale confirmationలో లోపం వచ్చింది. "
            "మళ్లీ ప్రయత్నించే ముందు తాజా వివరాలు చూడండి.",
            http_status=500,
        )