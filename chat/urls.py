from django.urls import path
from .views import get_access_token, get_chat_api_url, render_chat

urlpatterns = [
    path("", render_chat),
    path("get-api-url/", get_chat_api_url),
    path("get-access-token/", get_access_token),
]
