import requests
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from pandacare.settings import API_BASE_URL, CHAT_API_URL
from .utils import process_chat_data


# Create your views here.
def render_chat(req: HttpRequest):
    jwt = req.session.get("access_token")

    if not jwt:
        return render(req, "chat/error.html", {"error": "Authentication required"})

    res = requests.get(
        f"{CHAT_API_URL}/api/rest/chat/rooms",
        headers={"Authorization": f"Bearer {jwt}"},
    )

    if not res.ok:
        return render(req, "chat/error.html", {"error": "Failed to fetch chat rooms"})

    try:
        raw_room_data = res.json()
    except requests.JSONDecodeError:
        return render(
            req, "chat/error.html", {"error": "Invalid response from chat API"}
        )

    chat_rooms_and_messages = process_chat_data(jwt, raw_room_data)

    http_res = render(
        req,
        "chat/chat.html",
        {"chat_rooms": chat_rooms_and_messages, "user_id": req.session["user_id"]},
    )

    http_res.set_cookie(key="access_token", value=jwt, httponly=True)

    return http_res


def get_chat_api_url(req: HttpRequest) -> HttpResponse:
    return HttpResponse(CHAT_API_URL.encode())


def get_access_token(req: HttpRequest) -> HttpResponse:
    return HttpResponse(req.session["access_token"].encode())
