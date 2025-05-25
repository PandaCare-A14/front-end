def process_chat_data(raw_data):
    processed_data = []

    for room in raw_data:
        room_id = room[0]["$binary"]["base64"]  # Extract room ID
        messages = []

        for message in room[1]:
            messages.append({
                "id": message["_id"]["$oid"],
                "content": message["content"],
                "delivered": message["delivered"],
                "recipient_id": message["recipient_id"],
                "sender_id": message["sender_id"],
                "timestamp": int(message["timestamp"]["$date"]["$numberLong"]),
                "last_updated": int(message["last_updated"]["$date"]["$numberLong"]),
            })

        processed_data.append({
            "room_id": room_id,
            "messages": messages
        })

    return processed_data