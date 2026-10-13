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

]

