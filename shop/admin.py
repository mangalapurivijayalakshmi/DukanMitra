from django.contrib import admin
from .models import Supplier, Product, Sale, Customer
from .models import ReorderOrder,Expense, Payment, StockMovement

admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(Customer)
admin.site.register(ReorderOrder)
admin.site.register(Expense)
admin.site.register(Payment)
admin.site.register(StockMovement)