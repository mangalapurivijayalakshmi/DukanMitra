from django.contrib import admin
from .models import Supplier, Product, Sale, Customer, ReorderOrder, Expense, Payment, StockMovement

for m in (Supplier, Product, Sale, Customer, ReorderOrder, Expense, Payment, StockMovement):
    admin.site.register(m)