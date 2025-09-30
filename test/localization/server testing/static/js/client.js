document.addEventListener("DOMContentLoaded", () => {
  const dataDiv = document.getElementById("data");

  const socket = new WebSocket("ws://" + window.location.host + "/ws/data");
  socket.onopen = () => {
    console.log("Connected via WebSocket");
  };
  socket.onmessage = (event) => {
    let obj;
    try {
      obj = JSON.parse(event.data);
    } catch (e) {
      console.error("Invalid JSON:", event.data);
      return;
    }
    dataDiv.textContent = "Counter: " + obj.counter;
  };
  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
  socket.onclose = (event) => {
    console.log("WebSocket closed", event);
  };
});
