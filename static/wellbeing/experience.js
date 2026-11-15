// Small progressive enhancements for the wellbeing pages. Everything works without it.
(() => {
  "use strict";

  // Live UTC mission clock in the top bar.
  const clock = document.querySelector("[data-utc-clock]");
  if (clock) {
    const tick = () => { clock.textContent = `UTC ${new Date().toISOString().slice(11, 19)}`; };
    tick();
    setInterval(tick, 1000);
  }

  // Highlight the current tab in the phone tab bar.
  document.querySelectorAll(".tabbar a").forEach((link) => {
    const path = new URL(link.href).pathname;
    if (location.pathname === path || (path !== "/" && location.pathname.startsWith(path))) link.setAttribute("aria-current", "page");
  });

  // Sleep slider: show the chosen value.
  document.querySelectorAll("[data-range-output]").forEach((input) => {
    const output = document.getElementById(input.dataset.rangeOutput);
    const update = () => {
      output.textContent = Number(input.value).toFixed(1);
      input.style.setProperty("--fill", `${((input.value - input.min) / (input.max - input.min)) * 100}%`);
    };
    input.addEventListener("input", update);
    update();
  });

  // Check-in / re-check progress: count answered questions.
  document.querySelectorAll("[data-progress-form]").forEach((form) => {
    const groups = [...form.querySelectorAll("[data-question]")];
    const bar = form.querySelector("[data-progress-bar]");
    const label = form.querySelector("[data-progress-label]");
    const update = () => {
      const answered = groups.filter((group) => group.querySelector("input:checked") || group.dataset.question === "always").length;
      groups.forEach((group) => group.classList.toggle("is-answered", Boolean(group.querySelector("input:checked"))));
      if (bar) bar.style.width = `${(answered / groups.length) * 100}%`;
      if (label) label.textContent = answered === groups.length ? "All set: ready when you are" : `${answered} of ${groups.length} answered`;
      form.classList.toggle("is-complete", answered === groups.length);
    };
    form.addEventListener("change", update);
    update();
  });

  // Profile page: live avatar preview, drag-and-drop upload, and live name card.
  const avatarInput = document.querySelector("[data-avatar-input]");
  if (avatarInput) {
    const image = document.querySelector("[data-avatar-img]");
    const initials = document.querySelector("[data-avatar-initials]");
    const clear = document.querySelector("[data-avatar-clear]");
    const originalSrc = image.getAttribute("src");
    let objectUrl = null;
    const show = (src) => {
      image.hidden = !src;
      initials.hidden = Boolean(src);
      if (src) { image.src = src; image.alt = "Preview of your new profile photo"; }
    };
    avatarInput.addEventListener("change", () => {
      const file = avatarInput.files[0];
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = null;
      if (file && ["image/jpeg", "image/png", "image/webp"].includes(file.type) && file.size <= 5 * 1024 * 1024) {
        objectUrl = URL.createObjectURL(file);
        show(objectUrl);
        if (clear) clear.checked = false;
      } else {
        show(clear?.checked ? null : originalSrc);
      }
    });
    clear?.addEventListener("change", () => show(clear.checked ? null : objectUrl || originalSrc));

    const zone = document.querySelector("[data-dropzone]");
    if (zone) {
      ["dragenter", "dragover"].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.add("is-over"); }));
      ["dragleave", "drop"].forEach((name) => zone.addEventListener(name, () => zone.classList.remove("is-over")));
      zone.addEventListener("drop", (event) => {
        event.preventDefault();
        if (!event.dataTransfer?.files.length) return;
        try {
          avatarInput.files = event.dataTransfer.files;
          avatarInput.dispatchEvent(new Event("change", { bubbles: true }));
        } catch { /* Older browsers: the click-to-upload path still works. */ }
      });
    }

    document.querySelectorAll("[data-live-source]").forEach((input) => {
      const target = document.querySelector(`[data-live="${input.id}"]`);
      if (!target) return;
      input.addEventListener("input", () => {
        target.textContent = input.value.trim() || target.dataset.fallback;
        if (input.hasAttribute("data-initials-source") && !initials.hidden) {
          const letters = input.value.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
          if (letters) initials.textContent = letters;
        }
      });
    });
  }

  // Crew directory: search plus status filter.
  const crewFilter = document.querySelector("[data-crew-filter]");
  if (crewFilter) {
    const cards = [...document.querySelectorAll("[data-crew-card]")];
    const search = crewFilter.querySelector("[data-crew-search]");
    const count = crewFilter.querySelector("[data-crew-count]");
    const none = document.querySelector("[data-crew-none]");
    const apply = () => {
      const query = search.value.trim().toLocaleLowerCase();
      const status = crewFilter.querySelector("input[name='crew-status']:checked")?.value || "";
      let shown = 0;
      cards.forEach((card) => {
        const visible = (!status || card.dataset.status === status) && card.textContent.toLocaleLowerCase().includes(query);
        card.hidden = !visible;
        if (visible) shown += 1;
      });
      count.textContent = `${shown} of ${cards.length}`;
      none.hidden = shown > 0;
    };
    search.addEventListener("input", apply);
    crewFilter.addEventListener("change", apply);
    apply();
  }

  // Recommendation page: keep the "selected world" label in sync with the chosen card.
  const chosenLabel = document.querySelector("[data-chosen-label]");
  if (chosenLabel) {
    document.querySelectorAll("input[name='scene']").forEach((input) => input.addEventListener("change", () => {
      chosenLabel.textContent = input.dataset.title;
    }));
  }
})();
