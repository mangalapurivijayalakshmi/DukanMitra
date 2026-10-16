import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

def pending_action_expiry():
    return timezone.now() + timedelta(minutes=10)

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)          # ఇంగ్లీష్ పేరు
    telugu_name = models.CharField(max_length=100)   # తెలుగు పేరు (బియ్యం)
    unit = models.CharField(max_length=20)           # kg, litre, packet
    stock = models.FloatField(default=0)             # ప్రస్తుత నిల్వ
    low_stock_limit = models.FloatField(default=10)  # ఇంతకంటే తక్కువైతే హెచ్చరిక
    price = models.FloatField(default=0)  # ఒక యూనిట్ ధర
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True
    )
    purchase_price = models.FloatField(default=0)
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.telugu_name})"


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField()
    total_amount = models.FloatField()
    date = models.DateField()
    payment_method = models.CharField(max_length=10, default="cash")  # cash / upi / credit
    bill_no = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} - {self.date}"


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    balance_due = models.FloatField(default=0)       # బాకీ (udhar)
    credit_since = models.DateField(null=True, blank=True)   # బాకీ మొదలైన తేదీ
    
    
    def __str__(self):
        return f"{self.name} - ₹{self.balance_due}"

class ReorderOrder(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("cancelled", "Cancelled"),
        ("delivered", "delivered"),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    items_json = models.TextField()  # [{"product": "బియ్యం", "quantity": 40, "unit": "kg"}]
    message = models.TextField(blank=True)  # supplier కి పంపే message
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.supplier.name} - {self.status}"

class Expense(models.Model):
    name = models.CharField(max_length=100)
    amount = models.FloatField()
    date = models.DateField()

    def __str__(self):
        return f"{self.name} ₹{self.amount}"


class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount = models.FloatField()
    method = models.CharField(max_length=10, default="cash")
    date = models.DateField(auto_now_add=True)


class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    change = models.FloatField()
    reason = models.CharField(max_length=20)
    ref = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PendingAction(models.Model):
    class ActionType(models.TextChoices):
        RECORD_SALE = "record_sale", "Record sale"
        RECORD_PAYMENT = "record_payment", "Record payment"
        ADD_EXPENSE = "add_expense", "Add expense"
        APPROVE_REORDER = "approve_reorder", "Approve reorder"
        CANCEL_REORDER = "cancel_reorder", "Cancel reorder"
        MARK_DELIVERED = "mark_delivered", "Mark delivered"
        APPLY_BILL = "apply_bill", "Apply bill"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        EXECUTING = "executing", "Executing"
        EXECUTED = "executed", "Executed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session_key = models.CharField(
        max_length=64,
        db_index=True,
        editable=False,
    )

    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices,
    )

    arguments = models.JSONField(
        default=dict,
    )

    preview = models.JSONField(
        default=dict,
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )

    result = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField(
        default=pending_action_expiry,
    )

    executed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["session_key", "status"],
                name="pending_session_status_idx",
            ),
        ]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.action_type} - {self.status} - {self.id}"
