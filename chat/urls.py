from django.urls import path
from .views import render_chat

urlpatterns = [
    path("", render_chat)
]
