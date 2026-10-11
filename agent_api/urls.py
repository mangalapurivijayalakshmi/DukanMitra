from django.urls import path
from . import views

urlpatterns = [
    path("", views.home),
    path("api/chat", views.chat_api),
    path("api/dashboard", views.dashboard_api),
]