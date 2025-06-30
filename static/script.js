document.addEventListener("DOMContentLoaded", () => {
  // Tab switching
  const tabs = document.querySelectorAll("[data-tab]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      document.querySelectorAll(".tab-content").forEach((content) => {
        content.classList.remove("active");
      });
      document.getElementById(tab.dataset.tab).classList.add("active");
    });
  });

  // Chat functionality
  const conversation = document.getElementById("conversation");
  const messageInput = document.getElementById("message-input");
  const sendButton = document.getElementById("send-button");

  function addMessage(text, type) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${type}-message`;
    msgDiv.innerHTML = text;
    conversation.appendChild(msgDiv);
    conversation.scrollTop = conversation.scrollHeight;
  }

  async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, "user");
    messageInput.value = "";

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      const data = await response.json();
      if (data.error) throw new Error(data.error);

      addMessage(data.response, "ai");
    } catch (error) {
      addMessage(`Error: ${error.message}`, "error");
    }
  }

  sendButton.addEventListener("click", sendMessage);
  messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // File upload
  const fileInput = document.getElementById("file-input");
  const uploadButton = document.getElementById("upload-button");
  const filePreview = document.getElementById("file-preview");

  uploadButton.addEventListener("click", async () => {
    if (!fileInput.files.length) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (data.error) throw new Error(data.error);

      filePreview.innerHTML = `
                <h3>Document Analysis:</h3>
                <div class="ai-message">${data.response}</div>
                <h4>Preview:</h4>
                <p>${data.preview}</p>
            `;
    } catch (error) {
      filePreview.innerHTML = `<div class="error">${error.message}</div>`;
    }
  });
});
