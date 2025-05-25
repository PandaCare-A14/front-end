let socket = WebSocket(`${CHAT_API_URL}/api/ws`);

let form = document.getElementById("chat-form");

form.addEventListener("submit", function (e) {
  e.preventDefault();

  const input = document.getElementById("chat-message-input");
  let message = input.value.trim();

  if (message.length() == 0) {
    return;
  }

  let payload = {}

  socket.send("")
});
