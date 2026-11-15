(() => {
  "use strict";
  // Only appearance preferences live in localStorage. Personnel data stays on the server.
  const key = "astrodoctor-ui-v1";
  const themes = ["light", "dark"];
  let theme = "dark";
  try {
    const saved = JSON.parse(localStorage.getItem(key) || "{}");
    if (themes.includes(saved.theme)) theme = saved.theme;
  } catch { /* Storage can be unavailable on private or restricted devices. */ }
  function apply() {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem(key, JSON.stringify({ theme })); } catch { /* Session-only preferences still work. */ }
  }
  apply();
  const themeControl = document.getElementById("appearance-theme");
  if (themeControl) {
    themeControl.value = theme;
    themeControl.addEventListener("change", () => { theme = themeControl.value; apply(); });
  }
  window.addEventListener("storage", (event) => {
    if (event.key !== key) return;
    try {
      const saved = JSON.parse(event.newValue);
      if (!themes.includes(saved?.theme)) return;
      theme = saved.theme;
      document.documentElement.dataset.theme = theme;
      if (themeControl) themeControl.value = theme;
    } catch { /* Ignore invalid settings from other tabs. */ }
  });
  document.querySelectorAll(".main-nav a, .site-footer nav a").forEach((link) => {
    const path = new URL(link.href).pathname;
    if (location.pathname === path || (path !== "/" && location.pathname.startsWith(path))) link.setAttribute("aria-current", "page");
  });
  const connection = document.getElementById("connection-status");
  const updateConnection = () => { if (connection) { connection.textContent = navigator.onLine ? "● Online" : "○ Offline · reconnect to check in"; connection.dataset.online = String(navigator.onLine); } };
  updateConnection();
  window.addEventListener("online", updateConnection);
  window.addEventListener("offline", updateConnection);
  document.querySelectorAll(".message").forEach((message) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "dismiss-message";
    button.textContent = "×";
    button.setAttribute("aria-label", "Dismiss notification");
    button.addEventListener("click", () => message.remove());
    message.append(button);
  });
  const back = document.getElementById("back-to-top");
  if (back) {
    const update = () => { back.hidden = window.scrollY < 300; };
    window.addEventListener("scroll", update, { passive: true });
    update();
    back.addEventListener("click", () => window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" }));
  }
  const crewGrid = document.querySelector(".crew-grid:not(.developer-grid)");
  if (crewGrid && crewGrid.querySelector("a.crew-card")) {
    const toolbar = document.createElement("div");
    toolbar.className = "crew-toolbar";
    toolbar.innerHTML = '<label for="crew-search">Find a crew member</label><input id="crew-search" type="search" placeholder="Search name, role, or mission…"><span role="status"></span>';
    crewGrid.before(toolbar);
    const cards = [...crewGrid.querySelectorAll("a.crew-card")];
    const input = toolbar.querySelector("input");
    const count = toolbar.querySelector("span");
    function filter() {
      const query = input.value.trim().toLocaleLowerCase();
      cards.forEach((card) => { card.hidden = !card.textContent.toLocaleLowerCase().includes(query); });
      count.textContent = `${cards.filter((card) => !card.hidden).length} of ${cards.length} crew members`;
    }
    input.addEventListener("input", filter);
    filter();
  }
  document.querySelectorAll("form.profile-form").forEach((form) => {
    let dirty = false;
    let submitting = false;
    form.addEventListener("input", () => { dirty = true; });
    form.addEventListener("change", () => { dirty = true; });
    window.addEventListener("beforeunload", (event) => { if (dirty && !submitting) { event.preventDefault(); event.returnValue = ""; } });
    const photo = form.querySelector('input[type="file"][name="photo"]');
    if (photo) {
      let objectUrl;
      const preview = document.createElement("img");
      preview.className = "crew-portrait photo-preview";
      preview.alt = "New portrait preview";
      preview.hidden = true;
      photo.after(preview);
      photo.addEventListener("change", () => {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        preview.hidden = true;
        const file = photo.files[0];
        photo.setCustomValidity("");
        if (!file) return;
        if (file.size > 5 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
          photo.setCustomValidity("Choose a JPEG, PNG, or WebP photo of 5 MB or smaller.");
          photo.reportValidity();
          return;
        }
        objectUrl = URL.createObjectURL(file);
        preview.src = objectUrl;
        preview.hidden = false;
        const clear = form.querySelector('[name="photo-clear"]');
        if (clear) clear.checked = false;
      });
    }
    form.querySelectorAll("textarea[maxlength]").forEach((textarea) => {
      const counter = document.createElement("span");
      counter.className = "fine-print character-count";
      textarea.after(counter);
      const update = () => { counter.textContent = `${textarea.value.length} / ${textarea.maxLength} characters`; };
      textarea.addEventListener("input", update);
      update();
    });
    form.addEventListener("submit", () => {
      submitting = true;
      const button = form.querySelector('[type="submit"]');
      button.disabled = true;
      button.dataset.originalText = button.textContent;
      button.textContent = "Saving…";
      form.setAttribute("aria-busy", "true");
    });
    window.addEventListener("pageshow", () => {
      submitting = false;
      form.removeAttribute("aria-busy");
      const button = form.querySelector('[type="submit"]');
      button.disabled = false;
      if (button.dataset.originalText) button.textContent = button.dataset.originalText;
    });
  });
})();
