from django.db import models


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
    price = models.FloatField(default=0)             # ఒక యూనిట్ ధర
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.name} ({self.telugu_name})"


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField()
    total_amount = models.FloatField()
    date = models.DateField()

    def __str__(self):
        return f"{self.product.name} - {self.quantity} - {self.date}"


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    balance_due = models.FloatField(default=0)       # బాకీ (udhar)

    def __str__(self):
        return f"{self.name} - ₹{self.balance_due}"

class ReorderOrder(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("cancelled", "Cancelled"),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    items_json = models.TextField()  # [{"product": "బియ్యం", "quantity": 40, "unit": "kg"}]
    message = models.TextField(blank=True)  # supplier కి పంపే message
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.supplier.name} - {self.status}"