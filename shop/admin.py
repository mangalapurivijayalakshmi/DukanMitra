from django.contrib import admin
from .models import Supplier, Product, Sale, Customer

admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(Customer)
