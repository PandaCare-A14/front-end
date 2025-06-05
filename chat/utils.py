import uuid
from django.utils.http import base64
import requests
from pandacare.settings import API_BASE_URL, AUTH_API_URL


def process_chat_data(jwt: str, raw_data: dict):
    processed_data = []

    for room in raw_data:
        room_id_b64: str = room[0]  # Extract room ID
        room_id = convert_bson_uuid_to_python_uuid(room_id_b64)
        messages = []

        for message in room[1]:
            messages.append(
                {
                    "id": message["_id"]["$oid"],
                    "content": message["content"],
                    "delivered": message["delivered"],
                    "recipient_id": message["recipient_id"],
                    "sender_id": message["sender_id"],
                    "timestamp": int(message["timestamp"]["$date"]["$numberLong"]),
                    "last_updated": int(
                        message["last_updated"]["$date"]["$numberLong"]
                    ),
                }
            )

        endpoints_to_try = [
            f"{API_BASE_URL}/api/doctors/{room_id}",
            f"{API_BASE_URL}/api/profile",
        ]

        partner_profile_dict: dict[str, str] = partner_profile.json()
        partner_name = partner_profile_dict["name"]

        processed_data.append(
            {"room_id": room_id, "messages": messages, "partner_name": partner_name}
        )

    return processed_data


def convert_bson_uuid_to_python_uuid(bson_uuid_data):
    if not isinstance(bson_uuid_data, dict):
        print("Error: Input data is not a dictionary.")
        return None

    binary_info = bson_uuid_data.get("$binary")
    if not isinstance(binary_info, dict):
        print("Error: '$binary' field missing or not a dictionary.")
        return None

    base64_encoded_bytes = binary_info.get("base64")
    subtype = binary_info.get("subType")

    if subtype != "04":
        print(f"Error: Expected subType '04' for UUID, but got '{subtype}'.")
        return None

    if not base64_encoded_bytes:
        print("Error: 'base64' field is missing.")
        return None

    try:
        # Decode the base64 string to bytes
        uuid_bytes = base64.b64decode(base64_encoded_bytes)

        if len(uuid_bytes) != 16:
            print(
                f"Error: Decoded bytes length is {len(uuid_bytes)}, expected 16 for a UUID."
            )
            return None

        uuid_obj = uuid.UUID(bytes=uuid_bytes)
        return uuid_obj
    except Exception as e:
        print(f"Error during conversion: {e}")
        return None
