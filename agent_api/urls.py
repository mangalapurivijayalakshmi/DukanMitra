from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path("api/chat", views.chat_api),
    path("api/dashboard", views.dashboard_api),
    path("api/orders", views.orders_api),
    path("api/order-action", views.order_action),
    path("api/draft", views.draft_api),
    path("api/payment", views.payment_api),
    path("api/scan-bill", views.scan_bill_api),
    path("api/apply-bill", views.apply_bill_api),
    # PWA
    path("manifest.json", views.manifest),
    path("sw.js", views.service_worker),
    path("icon-<int:size>.png", views.icon),

]

