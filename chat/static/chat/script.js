let socket = new WebSocket(`${CHAT_API_URL}/api/ws`);
let currentRoomId = null;
let currentRecipientId = null; // Store the recipient ID for the current room

let form = document.getElementById("chat-form");

// Select chatroom
function selectRoom(roomId, recipientId, messages) {
  currentRoomId = roomId;
  currentRecipientId = recipientId; // Set the recipient ID directly

  document.getElementById("messages").innerHTML = ""; // Clear messages
  renderMessages(messages); // Render the messages passed from the backend
}

// Render messages in the chat window
function renderMessages(messages) {
  const messagesContainer = document.getElementById("messages");
  messages.forEach(message => {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("p-2", "rounded", "mb-2", "max-w-xs");

    if (message.sender_id === currentRecipientId) {
      messageDiv.classList.add("bg-blue-500", "text-white", "self-end");
    } else {
      messageDiv.classList.add("bg-gray-200", "text-black", "self-start");
    }

    messageDiv.textContent = message.content;
    messagesContainer.appendChild(messageDiv);
  });

  messagesContainer.scrollTop = messagesContainer.scrollHeight; // Scroll to the bottom
}

// Handle form submission
form.addEventListener("submit", function(e) {
  e.preventDefault();

  const input = document.getElementById("chat-message-input");
  let message = input.value.trim();

  if (message.length === 0) {
    return;
  }

  let payload = {
    "message_type": "message",
    "content": message,
    "recipient_id": currentRecipientId // Use the dynamically set recipient ID
  };

  socket.send(JSON.stringify(payload));
  input.value = ""; // Clear input
});

// Handle incoming messages via WebSocket
socket.onmessage = function(event) {
  const data = JSON.parse(event.data);

  if (data.room_id === currentRoomId) {
    renderMessages([data]);
  }
};
