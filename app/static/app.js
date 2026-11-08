const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const messageBox = document.getElementById("message");
const renderBox = document.getElementById("render-box");
const renderLabel = document.getElementById("render-target-label");
const renderText = document.getElementById("render-text");
const copyBtn = document.getElementById("copy-btn");

function addTurn(role, text) {
  const div = document.createElement("div");
  div.className = "turn " + role;
  const strong = document.createElement("strong");
  strong.textContent = role === "user" ? "You" : "Rocco V";
  const p = document.createElement("p");
  p.textContent = text;
  div.appendChild(strong);
  div.appendChild(p);
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function applyResult(result) {
  if (result.user_message) {
    addTurn("user", result.user_message);
  }
  const errorText = result.error || result.detail;
  if (errorText) {
    addTurn("assistant", "⚠ " + errorText);
    return;
  }
  if (result.assistant_message) {
    addTurn("assistant", result.assistant_message);
  }
  if (!result.assistant_message && !result.rendered) {
    addTurn("assistant", "⚠ No response came back — check the container logs.");
  }
  if (result.rendered) {
    renderLabel.textContent = result.target_label || "Rendered prompt";
    renderText.textContent = result.rendered;
    renderBox.hidden = false;
    renderBox.scrollIntoView({ behavior: "smooth" });
  }
}

async function postJson(url, options) {
  try {
    const res = await fetch(url, options);
    return await res.json();
  } catch (err) {
    return { error: "Couldn't reach the server (" + err.message + ")." };
  }
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = messageBox.value.trim();
  if (!message) return;
  messageBox.value = "";
  const result = await postJson("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: "message=" + encodeURIComponent(message),
  });
  applyResult(result);
});

document.querySelectorAll(".target-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    addTurn("user", "(Render for " + btn.textContent + ")");
    const result = await postJson("/render/" + btn.dataset.target, { method: "POST" });
    result.user_message = null;
    applyResult(result);
  });
});

copyBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(renderText.textContent);
  copyBtn.textContent = "Copied!";
  setTimeout(() => (copyBtn.textContent = "Copy"), 1500);
});
