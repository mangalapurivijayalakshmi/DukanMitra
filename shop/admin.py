from django.contrib import admin
from .models import Supplier, Product, Sale, Customer
from .models import ReorderOrder

admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(Customer)
admin.site.register(ReorderOrder)