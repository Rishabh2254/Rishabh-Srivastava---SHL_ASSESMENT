(function () {
  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async function run() {
    const params = new URLSearchParams(window.location.search);
    const name = params.get("name") || "";
    const titleEl = document.getElementById("assessmentTitle");
    const contentEl = document.getElementById("assessmentContent");

    if (!name) {
      titleEl.textContent = "Assessment not found";
      contentEl.innerHTML = "<p>No assessment name was provided.</p>";
      return;
    }

    titleEl.textContent = name;

    let index = {};
    try {
      const response = await fetch("./assets/catalog_index.json");
      index = await response.json();
    } catch (error) {
      contentEl.innerHTML = `<p>Could not load catalog index: ${escapeHtml(error.message)}</p>`;
      return;
    }

    const details = index[name];
    if (!details) {
      contentEl.innerHTML = `<p>No mapped details found for <strong>${escapeHtml(name)}</strong>.</p>`;
      return;
    }

    contentEl.innerHTML = `
      <article class="assessment-detail-card">
        <div class="assessment-field-label">Name</div>
        <div class="assessment-field-value">${escapeHtml(details.name || name)}</div>

        <div class="assessment-field-label">Test Type</div>
        <div class="assessment-field-value">${escapeHtml(details.test_type || "Not specified")}</div>

        <div class="assessment-field-label">Description</div>
        <div class="assessment-field-value">${escapeHtml(details.description || "Not specified")}</div>

        <div class="assessment-field-label">Duration</div>
        <div class="assessment-field-value">${escapeHtml(details.duration || "Not specified")}</div>

        <div class="assessment-field-label">Category</div>
        <div class="assessment-field-value">${escapeHtml(details.category || "Not specified")}</div>

        <div class="assessment-field-label">Skills</div>
        <div class="assessment-field-value">${escapeHtml(Array.isArray(details.skills) && details.skills.length ? details.skills.join(", ") : "Not specified")}</div>

        <div class="assessment-field-label">Delivery</div>
        <div class="assessment-field-value">Remote: ${escapeHtml(details.remote_support || "Unknown")} | Adaptive: ${escapeHtml(details.adaptive_support || "Unknown")}</div>

        <div class="assessment-field-label">SHL URL</div>
        <div class="assessment-field-value"><a href="${escapeHtml(details.url || "")}" target="_blank" rel="noopener noreferrer">${escapeHtml(details.url || "Unavailable")}</a></div>

        <p class="dialog-note">SHL may redirect legacy product URLs to broader landing pages. This page is the exact mapped assessment from your local catalog data.</p>
      </article>
    `;
  }

  run();
})();
