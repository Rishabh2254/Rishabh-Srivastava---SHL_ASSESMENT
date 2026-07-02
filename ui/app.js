const state = {
  sessions: [],
  activeSessionId: null,
  messages: [],
  recommendations: [],
  loading: false,
  catalogIndex: {},
};

const elements = {
  chatHistoryList: document.getElementById("chatHistoryList"),
  messages: document.getElementById("messages"),
  recommendationsPanel: document.getElementById("recommendationsPanel"),
  recommendationsList: document.getElementById("recommendationsList"),
  composer: document.getElementById("composer"),
  messageInput: document.getElementById("messageInput"),
  statusBadge: document.getElementById("statusBadge"),
  messageTemplate: document.getElementById("messageTemplate"),
  promptChips: Array.from(document.querySelectorAll(".prompt-chip")),
  newChatButton: document.getElementById("newChatButton"),
  assessmentDialog: document.getElementById("assessmentDialog"),
  dialogTitle: document.getElementById("dialogTitle"),
  dialogBody: document.getElementById("dialogBody"),
  closeDialogButton: document.getElementById("closeDialogButton"),
};

const API_BASE_URL = "https://rishabh-srivastava-shl-assesment.onrender.com";
const STORAGE_KEY = "shl_chat_sessions_v1";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function nowIso() {
  return new Date().toISOString();
}

function storageAvailable() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function loadSessions() {
  if (!storageAvailable()) {
    return [];
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((session) => session && session.id && Array.isArray(session.messages));
  } catch {
    return [];
  }
}

function saveSessions() {
  if (!storageAvailable()) {
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.sessions));
}

function deriveSessionTitle(session) {
  const firstUser = session.messages.find((m) => m.role === "user");
  if (!firstUser || !firstUser.content) {
    return "New chat";
  }
  return firstUser.content.length > 42
    ? `${firstUser.content.slice(0, 42)}...`
    : firstUser.content;
}

function setActiveSession(sessionId) {
  const session = state.sessions.find((item) => item.id === sessionId);
  if (!session) {
    return;
  }
  state.activeSessionId = session.id;
  state.messages = session.messages;
  state.recommendations = session.recommendations || [];
  renderHistory();
  renderMessages();
  renderRecommendations();
}

function syncActiveSession() {
  const session = state.sessions.find((item) => item.id === state.activeSessionId);
  if (!session) {
    return;
  }
  session.messages = state.messages;
  session.recommendations = state.recommendations;
  session.updatedAt = nowIso();
  session.title = deriveSessionTitle(session);
  saveSessions();
  renderHistory();
}

function createSession() {
  const session = {
    id: `session-${Date.now()}`,
    title: "New chat",
    createdAt: nowIso(),
    updatedAt: nowIso(),
    messages: [
      {
        role: "assistant",
        content:
          "Describe the role you are hiring for, and I will clarify requirements before recommending SHL assessments.",
      },
    ],
    recommendations: [],
  };
  state.sessions.unshift(session);
  saveSessions();
  setActiveSession(session.id);
}

function renderHistory() {
  elements.chatHistoryList.innerHTML = "";
  if (!state.sessions.length) {
    elements.chatHistoryList.innerHTML = "<p class=\"history-empty\">No chats yet.</p>";
    return;
  }
  for (const session of state.sessions) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `history-item ${session.id === state.activeSessionId ? "active" : ""}`;
    button.innerHTML = `
      <span class="history-title">${escapeHtml(session.title || "New chat")}</span>
      <span class="history-time">${new Date(session.updatedAt).toLocaleString()}</span>
    `;
    button.addEventListener("click", () => setActiveSession(session.id));
    elements.chatHistoryList.appendChild(button);
  }
}

function setStatus(kind, text) {
  elements.statusBadge.textContent = text;
  elements.statusBadge.className = `status-badge status-${kind}`;
}

function renderMessages() {
  elements.messages.innerHTML = "";
  for (const message of state.messages) {
    const fragment = elements.messageTemplate.content.cloneNode(true);
    const article = fragment.querySelector(".message");
    const role = fragment.querySelector(".message-role");
    const bubble = fragment.querySelector(".message-bubble");

    article.classList.add(message.role);
    role.textContent = message.role === "assistant" ? "Assistant" : "You";
    bubble.textContent = message.content;

    elements.messages.appendChild(fragment);
  }
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function detailUrlFor(name) {
  return `./assessment.html?name=${encodeURIComponent(name)}`;
}

function renderRecommendations() {
  if (!state.recommendations.length) {
    elements.recommendationsPanel.classList.add("hidden");
    elements.recommendationsList.innerHTML = "";
    return;
  }

  elements.recommendationsPanel.classList.remove("hidden");
  elements.recommendationsList.innerHTML = "";

  for (const item of state.recommendations) {
    const card = document.createElement("article");
    card.className = "recommendation-card";
    card.innerHTML = `
      <h4>${escapeHtml(item.name)}</h4>
      <a href="${escapeHtml(detailUrlFor(item.name))}" class="assessment-link">Open mapped assessment details</a>
      <div class="recommendation-meta">Test type: ${escapeHtml(item.test_type)}</div>
    `;
    card.addEventListener("click", () => openAssessmentDialog(item));
    card.querySelector("a").addEventListener("click", (event) => event.stopPropagation());
    elements.recommendationsList.appendChild(card);
  }
}

function openAssessmentDialog(item) {
  const details = state.catalogIndex[item.name] || null;
  elements.dialogTitle.textContent = item.name;
  elements.dialogBody.innerHTML = "";

  const entries = [
    ["Test Type", item.test_type],
    ["Description", details?.description || "Description unavailable in local catalog."],
    ["Duration", details?.duration || "Not specified"],
    ["Category", details?.category || "Not specified"],
    ["Skills", Array.isArray(details?.skills) && details.skills.length ? details.skills.join(", ") : "Not specified"],
    [
      "Delivery",
      details ? `Remote: ${details.remote_support || "Unknown"} | Adaptive: ${details.adaptive_support || "Unknown"}` : "Not specified",
    ],
    [
      "Mapped details page",
      `<a href="${escapeHtml(detailUrlFor(item.name))}">Open ${escapeHtml(item.name)} details</a>`,
      true,
    ],
  ];

  for (const [label, value, isHtml] of entries) {
    const section = document.createElement("section");
    section.innerHTML = `
      <div class="assessment-field-label">${escapeHtml(label)}</div>
      <div class="assessment-field-value">${isHtml ? value : escapeHtml(String(value))}</div>
    `;
    elements.dialogBody.appendChild(section);
  }

  if (typeof elements.assessmentDialog.showModal === "function") {
    elements.assessmentDialog.showModal();
  }
}

async function loadCatalogIndex() {
  try {
    const response = await fetch("./assets/catalog_index.json");
    if (!response.ok) {
      throw new Error(`catalog index status ${response.status}`);
    }
    state.catalogIndex = await response.json();
  } catch (error) {
    setStatus("error", "Catalog map unavailable");
  }
}

async function sendMessage(text) {
  const content = text.trim();
  if (!content || state.loading) {
    return;
  }

  state.messages = [...state.messages, { role: "user", content }];
  syncActiveSession();
  state.loading = true;
  elements.messageInput.value = "";
  setStatus("loading", "Calling API...");
  renderMessages();

  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: state.messages }),
    });

    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    const payload = await response.json();
    state.messages = [...state.messages, { role: "assistant", content: payload.reply || "" }];
    state.recommendations = Array.isArray(payload.recommendations) ? payload.recommendations : [];
    syncActiveSession();
    renderMessages();
    renderRecommendations();
    setStatus("idle", payload.end_of_conversation ? "Completed" : "Ready");
  } catch (error) {
    state.messages = [...state.messages, {
      role: "assistant",
      content: `The UI could not reach the API. ${error.message}`,
    }];
    syncActiveSession();
    renderMessages();
    renderRecommendations();
    setStatus("error", "Request failed");
  } finally {
    state.loading = false;
  }
}

function resetChat() {
  createSession();
  state.loading = false;
  setStatus("idle", "Ready");
}

elements.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendMessage(elements.messageInput.value);
});

elements.messageInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    await sendMessage(elements.messageInput.value);
  }
});

elements.newChatButton.addEventListener("click", resetChat);
elements.closeDialogButton.addEventListener("click", () => elements.assessmentDialog.close());
elements.assessmentDialog.addEventListener("click", (event) => {
  const rect = elements.assessmentDialog.getBoundingClientRect();
  const inDialog =
    rect.top <= event.clientY &&
    event.clientY <= rect.top + rect.height &&
    rect.left <= event.clientX &&
    event.clientX <= rect.left + rect.width;
  if (!inDialog) {
    elements.assessmentDialog.close();
  }
});

Promise.resolve(loadCatalogIndex()).finally(() => {
  state.sessions = loadSessions();
  if (!state.sessions.length) {
    createSession();
  } else {
    setActiveSession(state.sessions[0].id);
  }
  setStatus("idle", "Ready");
});
