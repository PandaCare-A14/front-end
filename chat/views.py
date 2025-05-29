import requests
from django.http import HttpRequest
from django.shortcuts import render
from pandacare.settings import CHAT_API_URL
from .utils import process_chat_data


# Create your views here.
def render_chat(req: HttpRequest):
    jwt = req.session.get("access_token")

    if not jwt:
        return render(req, "chat/error.html", {"error": "Authentication required"})

    print(jwt)

    res = requests.get(
        f"{CHAT_API_URL}/api/rest/chat/rooms",
        headers={"Authorization": f"Bearer {jwt}"},
    )

    print(f"{res}")

    if not res.ok:
        return render(req, "chat/error.html", {"error": "Failed to fetch chat rooms"})

    try:
        raw_room_data = res.json()
    except requests.JSONDecodeError:
        return render(
            req, "chat/error.html", {"error": "Invalid response from chat API"}
        )

    chat_rooms_and_messages = process_chat_data(raw_room_data)

    return render(
        req,
        "chat/chat.html",
        {"chat_rooms": chat_rooms_and_messages, "user_id": req.user_id},
    )
