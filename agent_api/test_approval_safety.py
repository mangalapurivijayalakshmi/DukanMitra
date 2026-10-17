from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from agent_api.approvals import process_pending_action
from shop.models import (
    Customer,
    PendingAction,
    Product,
    Sale,
    StockMovement,
)


class SaleApprovalSafetyTests(TestCase):
    def setUp(self):
        self.owner_session = "test-owner-session"
        self.other_session = "test-other-session"

        self.product = Product.objects.create(
            name="Test Sugar",
            telugu_name="టెస్ట్ చక్కెర",
            unit="kg",
            stock=5,
            low_stock_limit=10,
            price=45,
            purchase_price=36,
        )

        self.customer = Customer.objects.create(
            name="Test Ramesh",
            balance_due=1200,
        )

    def create_proposal(self, expired=False):
        expiry = timezone.now() + timedelta(minutes=10)

        if expired:
            expiry = timezone.now() - timedelta(minutes=1)

        return PendingAction.objects.create(
            session_key=self.owner_session,
            action_type=PendingAction.ActionType.RECORD_SALE,
            arguments={
                "product_id": self.product.pk,
                "customer_id": self.customer.pk,
                "quantity": 2.0,
                "payment_method": "credit",
                "unit_price": 45.0,
                "expected_total": 90.0,
            },
            preview={
                "product": self.product.telugu_name,
                "quantity": 2.0,
                "unit": "kg",
                "unit_price": 45.0,
                "total": 90.0,
                "payment_method": "credit",
                "stock_before": 5.0,
                "stock_after": 3.0,
                "customer": self.customer.name,
                "dues_before": 1200.0,
                "dues_after": 1290.0,
            },
            expires_at=expiry,
        )

    def snapshot(self):
        self.product.refresh_from_db()
        self.customer.refresh_from_db()

        return {
            "stock": self.product.stock,
            "dues": self.customer.balance_due,
            "sales": Sale.objects.count(),
            "movements": StockMovement.objects.count(),
        }

    def test_expired_proposal_cannot_execute(self):
        proposal = self.create_proposal(expired=True)
        before = self.snapshot()

        result = process_pending_action(
            owner_session_key=self.owner_session,
            action_id=str(proposal.pk),
            action="confirm",
        )

        proposal.refresh_from_db()

        self.assertFalse(result["success"])
        self.assertEqual(result["http_status"], 409)
        self.assertEqual(
            proposal.status,
            PendingAction.Status.EXPIRED,
        )
        self.assertEqual(before, self.snapshot())

    def test_other_session_cannot_confirm(self):
        proposal = self.create_proposal()
        before = self.snapshot()

        result = process_pending_action(
            owner_session_key=self.other_session,
            action_id=str(proposal.pk),
            action="confirm",
        )

        proposal.refresh_from_db()

        self.assertFalse(result["success"])
        self.assertEqual(result["http_status"], 404)
        self.assertEqual(
            proposal.status,
            PendingAction.Status.PENDING,
        )
        self.assertEqual(before, self.snapshot())

    def test_other_session_cannot_cancel(self):
        proposal = self.create_proposal()
        before = self.snapshot()

        result = process_pending_action(
            owner_session_key=self.other_session,
            action_id=str(proposal.pk),
            action="cancel",
        )

        proposal.refresh_from_db()

        self.assertFalse(result["success"])
        self.assertEqual(result["http_status"], 404)
        self.assertEqual(
            proposal.status,
            PendingAction.Status.PENDING,
        )
        self.assertEqual(before, self.snapshot())