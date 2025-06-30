document.addEventListener("DOMContentLoaded", () => {
  const conversation = document.getElementById("conversation");
  const messageInput = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");
  const uploadBtn = document.getElementById("upload-btn");
  const fileInput = document.getElementById("file-input");

  // Load conversation history
  loadHistory();

  // Send message handler
  sendBtn.addEventListener("click", sendMessage);
  messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // File upload handler
  uploadBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", handleFileUpload);

  function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, "user-message");
    messageInput.value = "";

    fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.error) {
          addMessage(data.error, "error-message");
        } else {
          addMessage(data.response, "ai-message", data.raw_response);
        }
      })
      .catch((error) => {
        addMessage("Connection error", "error-message");
      });
  }

  function handleFileUpload() {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    addMessage(`Uploading ${file.name}...`, "user-message");

    fetch("/api/upload", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.error) {
          addMessage(data.error, "error-message");
        } else {
          addMessage(`File processed: ${data.filename}`, "ai-message");
          addMessage(data.summary, "ai-message");
        }
      })
      .catch((error) => {
        addMessage("Upload failed", "error-message");
      });

    fileInput.value = "";
  }

  function addMessage(content, className, rawContent = null) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${className}`;

    if (className === "ai-message") {
      messageDiv.innerHTML = content;

      // Add feedback buttons
      if (rawContent) {
        const feedbackDiv = document.createElement("div");
        feedbackDiv.className = "feedback-buttons";
        feedbackDiv.innerHTML = `
                    <span>Was this helpful?</span>
                    <button class="feedback-btn" 
                            data-query="${encodeURIComponent(content)}" 
                            data-response="${encodeURIComponent(rawContent)}"
                            onclick="sendFeedback(this, true)">👍 Yes</button>
                    <button class="feedback-btn"
                            data-query="${encodeURIComponent(content)}" 
                            data-response="${encodeURIComponent(rawContent)}"
                            onclick="sendFeedback(this, false)">👎 No</button>
                `;
        messageDiv.appendChild(feedbackDiv);
      }
    } else {
      messageDiv.textContent = content;
    }

    conversation.appendChild(messageDiv);
    conversation.scrollTop = conversation.scrollHeight;
  }

  function loadHistory() {
    // In a real app, you would fetch this from your backend
    // For now we'll just show a welcome message
    addMessage("Hello! How can I help you today?", "ai-message");
  }
});

function sendFeedback(button, helpful) {
  const query = decodeURIComponent(button.dataset.query);
  const response = decodeURIComponent(button.dataset.response);

  button.disabled = true;
  button.textContent = helpful ? "Thanks! 👍" : "Thanks! 👎";

  fetch("/api/feedback", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      response,
      helpful,
    }),
  });
}
