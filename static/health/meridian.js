(() => {
  "use strict";
  const DB = "meridian-demo-v1";
  async function storage(action, key, value) {
    const db = await new Promise((resolve, reject) => {
      const request = indexedDB.open(DB, 1);
      request.onupgradeneeded = () => request.result.createObjectStore("state");
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return new Promise((resolve, reject) => {
      const tx = db.transaction("state", action === "get" ? "readonly" : "readwrite");
      const store = tx.objectStore("state");
      const request = action === "put" ? store.put(value, key) : action === "clear" ? store.clear() : store[action](key);
      tx.oncomplete = () => { db.close(); resolve(request.result); };
      tx.onabort = tx.onerror = () => { db.close(); reject(tx.error || new Error("Device storage unavailable.")); };
    });
  }
  // Account switching must not expose another demo account's local snapshot or queue.
  document.querySelectorAll('form[action$="/accounts/logout/"]').forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      try { await storage("delete", "snapshot"); } catch { /* An unavailable store cannot expose a cached view here. */ }
      form.submit();
    });
  });
  const app = document.getElementById("mission-app");
  if (!app) return;
  const feedback = document.getElementById("mission-feedback");
  const mode = document.getElementById("mission-mode");
  const pending = document.getElementById("mission-pending");
  const simulate = document.getElementById("mission-ground-offline");
  let snapshot, outbox = [], lastSync = null, syncing = false, mutation = Promise.resolve();
  const offline = () => !navigator.onLine || simulate.checked;
  const say = (message) => { feedback.textContent = message; };
  const node = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  };
  const button = (label, callback, className = "button button-secondary") => {
    const item = node("button", label, className);
    item.type = "button";
    item.addEventListener("click", callback);
    return item;
  };
  function updateStatus() {
    mode.textContent = `Mission day ${snapshot?.day || "—"} · ${offline() ? "Offline" : "Online"}`;
    pending.textContent = `${outbox.length} waiting · Last sync: ${lastSync ? new Date(lastSync).toLocaleString() : "not yet"}`;
  }
  function serialized(callback) {
    const next = mutation.then(callback);
    mutation = next.catch(() => {});
    return next;
  }
  async function queue(endpoint, payload, priority = 2) {
    await serialized(async () => {
      const next = [...outbox, { owner: snapshot.owner, endpoint, payload, priority, queuedAt: Date.now() }];
      await storage("put", `outbox-${snapshot.owner}`, next);
      outbox = next;
    });
    updateStatus();
    say("Saved on this device. Waiting to sync; new check-ins are assessed by the local service after delivery.");
    await sync();
  }
  async function sync() {
    if (offline() || syncing || !snapshot) return;
    syncing = true;
    try {
      const session = await fetch("/mission/session/", { credentials: "same-origin", cache: "no-store" });
      if (session.redirected || !session.ok || !(session.headers.get("content-type") || "").includes("application/json")) throw new Error("Sign in again before syncing.");
      if ((await session.json()).owner !== snapshot.owner) throw new Error("The account changed. Return to the signed-in account's overview before syncing.");
      for (const item of [...outbox].sort((a, b) => a.priority - b.priority || a.queuedAt - b.queuedAt)) {
        if (offline()) break;
        if (item.owner !== snapshot.owner) throw new Error("A queued item belongs to another account; sync stopped.");
        const token = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] || "";
        const response = await fetch(item.endpoint, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(token) }, body: JSON.stringify(item.payload) });
        if (response.redirected || !(response.headers.get("content-type") || "").includes("application/json")) throw new Error("Sign in again to send pending items.");
        const result = await response.json();
        if (!response.ok) throw new Error(`${result.error || "Sync failed"} The queued item is retained.`);
        await serialized(async () => {
          const remaining = outbox.filter((entry) => entry.payload.client_id !== item.payload.client_id);
          await storage("put", `outbox-${snapshot.owner}`, remaining);
          outbox = remaining;
        });
        lastSync = Date.now();
        await storage("put", `lastSync-${snapshot.owner}`, lastSync);
        say("Pending item synced successfully. Reload the overview to see updated assessments.");
      }
    } catch (error) {
      say(error instanceof TypeError ? "Connection unavailable. Pending items remain on this device." : error.message);
    } finally { syncing = false; updateStatus(); }
  }
  function chart(rows, metric, first, last, exposures) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 640 150");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `${metric.label} trend; gaps are missing observations, crossed points are excluded`);
    const values = rows.map(row => row.value);
    if (metric.median != null) values.push(metric.median - metric.spread * 3, metric.median + metric.spread * 3);
    if (!values.length) return node("p", "No observations in this range.", "muted");
    const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
    const x = day => 30 + (day - first) / Math.max(last - first, 1) * 580;
    const y = value => 120 - (value - min) / span * 100;
    const shape = (tag, attrs, title) => {
      const item = document.createElementNS(ns, tag);
      Object.entries(attrs).forEach(([key, value]) => item.setAttribute(key, value));
      if (title) { const t = document.createElementNS(ns, "title"); t.textContent = title; item.append(t); }
      svg.append(item); return item;
    };
    if (metric.median != null) {
      shape("rect", { x: 30, y: y(metric.median + metric.spread * 3), width: 580, height: 6 * metric.spread / span * 100, fill: "#65cbb8", opacity: ".15" });
      shape("line", { x1: 30, x2: 610, y1: y(metric.median), y2: y(metric.median), stroke: "#c8a94f", "stroke-dasharray": "4 4" });
    }
    exposures.forEach(event => shape("line", { x1: x(event.start_day), x2: x(event.start_day), y1: 15, y2: 123, stroke: "#9aa8bc", "stroke-dasharray": "2 5" }, `${event.exposure_type}, day ${event.start_day}`));
    let previous = null;
    rows.forEach(row => {
      if (row.accepted && previous && row.mission_day === previous.mission_day + 1) shape("line", { x1: x(previous.mission_day), y1: y(previous.value), x2: x(row.mission_day), y2: y(row.value), stroke: "#258978", "stroke-width": 2 });
      shape("circle", { cx: x(row.mission_day), cy: y(row.value), r: row.accepted ? 3 : 5, fill: row.accepted ? "#258978" : "none", stroke: row.accepted ? "#258978" : "#b34f43" }, `Day ${row.mission_day}: ${row.value} ${row.unit}${row.accepted ? "" : " · excluded: " + row.exclusion_reason}`);
      previous = row.accepted ? row : null;
    });
    shape("text", { x: 30, y: 145, fill: "currentColor", "font-size": 11 }).textContent = `Day ${first}`;
    shape("text", { x: 610, y: 145, fill: "currentColor", "font-size": 11, "text-anchor": "end" }).textContent = `Day ${last}`;
    return svg;
  }
  function showFinding(finding) {
    const details = finding.details;
    const panel = node("section", undefined, "card finding-reading");
    panel.id = `finding-${finding.id}`;
    panel.append(node("h2", `${details.glyph} ${finding.domain}: ${finding.level}`), node("p", `Day ${finding.mission_day} · ${finding.status} · ${snapshot.rule}`, "muted"));
    const section = (title, text) => panel.append(node("h3", title), node("p", text));
    section("What changed", details.what_changed);
    section("Why it matters", details.why_it_matters);
    section("Measurements", details.metrics.map(m => `${m.label}: ${m.value} ${m.unit}; baseline median ${m.median?.toFixed(2)} from ${m.sample_count} samples`).join(". "));
    section("Linked exposures", details.links.length ? details.links.map(link => `${link.type}, day ${link.start_day} · ${link.evidence_tag} · ${link.source}. ${link.association}`).join("\n") : "No qualifying association recorded.");
    section("Confidence", `${details.confidence}: ${details.confidence_reasons.join(" ")}`);
    section("Limits", details.limits);
    section("Next step", details.next_step);
    if (snapshot.can_write) {
      const reason = node("textarea");
      reason.maxLength = 2000;
      reason.placeholder = "Reason required to dismiss";
      reason.setAttribute("aria-label", "Dismissal reason");
      const actions = node("div", undefined, "checkin-actions");
      const act = async (action) => {
        actions.querySelectorAll("button").forEach(b => { b.disabled = true; });
        try {
          await queue(`/mission/finding/${finding.id}/action/`, { client_id: crypto.randomUUID(), action, reason: action === "dismiss" ? reason.value.trim() : "" }, action === "escalate" ? 0 : 1);
          actions.replaceChildren(node("p", "Action saved or queued. Assessed severity is unchanged."));
        } catch { say("Could not save the action to device storage. Please retry."); actions.querySelectorAll("button").forEach(b => { b.disabled = false; }); }
      };
      const dismiss = button("Dismiss", () => act("dismiss"));
      dismiss.disabled = true;
      reason.addEventListener("input", () => { dismiss.disabled = !reason.value.trim(); });
      actions.append(button("Acknowledge", () => act("acknowledge")), dismiss, button("Escalate to medical officer", () => act("escalate")));
      panel.append(reason, actions);
    }
    return panel;
  }
  function render() {
    app.replaceChildren();
    const banner = node("section", undefined, "mission-banner");
    banner.append(node("p", "MERIDIAN · SYNTHETIC", "eyebrow"), node("h1", `Overview · ${snapshot.astronaut.display_name}`), node("p", `Mission day ${snapshot.day} · Rule ${snapshot.rule}`));
    app.append(banner);
    const filters = node("form", undefined, "card mission-filters");
    filters.method = "get";
    filters.action = `/mission/astronaut/${snapshot.astronaut.id}/`;
    const dayLabel = node("label", "Mission day ");
    const dayInput = node("input"); Object.assign(dayInput, { type: "number", name: "day", min: "1", max: String(snapshot.latest_day), value: snapshot.day, required: true }); dayLabel.append(dayInput);
    const rangeLabel = node("label", "Trend range "); const range = node("select"); range.name = "days";
    [7, 14, 30].forEach(days => { const option = node("option", `${days} days`); option.value = days; option.selected = snapshot.days === days; range.append(option); }); rangeLabel.append(range);
    const excludedLabel = node("label", `Show excluded (${snapshot.excluded_count}) `); const excluded = node("input"); Object.assign(excluded, { type: "checkbox", name: "excluded", value: "1", checked: snapshot.observations.some(row => !row.accepted) }); excludedLabel.prepend(excluded);
    const submit = node("button", "Apply", "button button-primary"); submit.type = "submit";
    filters.append(dayLabel, rangeLabel, excludedLabel, submit);
    filters.addEventListener("submit", (event) => { if (!navigator.onLine) { event.preventDefault(); say("This device has the last-loaded view. Reconnect to load a different mission day or range."); } });
    app.append(filters);
    snapshot.quality_prompts.forEach(prompt => app.append(node("p", `${prompt.indicator_code}: ${prompt.value} — ${prompt.exclusion_reason} This value is excluded from health alerts.`, "message message-error")));
    const timeline = node("section"); timeline.id = "timeline";
    const exposurePanel = node("section", undefined, "card profile-detail"); exposurePanel.append(node("h2", "Exposure timeline"));
    const eventFilter = node("select"); eventFilter.setAttribute("aria-label", "Exposure type");
    ["All", ...new Set(snapshot.exposures.map(e => e.exposure_type))].forEach(type => { const option = node("option", type.replaceAll("_", " ")); option.value = type; eventFilter.append(option); });
    const eventRows = node("div"); const updateEvents = () => {
      eventRows.replaceChildren();
      snapshot.exposures.filter(e => eventFilter.value === "All" || e.exposure_type === eventFilter.value).forEach(event => eventRows.append(node("p", `Day ${event.start_day}–${event.end_day} · ${event.exposure_type.replaceAll("_", " ")} · ${event.scope} · ${event.magnitude} (${event.unit})`, "exposure-lane")));
      if (!eventRows.children.length) eventRows.append(node("p", "No exposures in this range.", "muted"));
    }; eventFilter.addEventListener("change", updateEvents); updateEvents(); exposurePanel.append(eventFilter, eventRows); timeline.append(exposurePanel);
    snapshot.domains.forEach(domain => {
      const card = node("section", undefined, "card mission-domain");
      card.append(node("h2", `${domain.glyph} ${domain.domain} · ${domain.level}`), node("p", domain.what_changed, "muted"));
      domain.metrics.forEach(metric => {
        const metricPanel = node("div", undefined, "mission-metric");
        metricPanel.append(node("h3", metric.label), node("p", `${metric.value ?? "Missing"} ${metric.unit} · ${metric.sample_count} prior baseline samples${metric.provisional ? " · Provisional" : ""} · Data age: ${metric.data_age == null ? "unavailable" : metric.data_age + " days"}`));
        if (!metric.accepted) metricPanel.append(node("p", metric.reason, "medical-note"));
        const rows = snapshot.observations.filter(row => row.indicator_code === metric.code);
        metricPanel.append(chart(rows, metric, Math.max(1, snapshot.day - snapshot.days + 1), snapshot.day, snapshot.exposures));
        card.append(metricPanel);
      });
      timeline.append(card);
    });
    timeline.append(node("p", "Bands show the selected day’s median ± 3 robust spreads for reference. Each historical assessment uses only its own earlier data. Dots have measurement tooltips; breaks show missing days.", "mission-honesty"));
    app.append(timeline);
    const findingList = node("section"); findingList.id = "findings";
    if (!snapshot.findings.length) findingList.append(node("p", "No sustained findings on this day. UNKNOWN domains still need data or baseline samples.", "mission-honesty"));
    snapshot.findings.forEach(finding => findingList.append(showFinding(finding)));
    app.append(findingList);
    if (snapshot.can_write) renderCheckin();
    app.append(node("p", snapshot.limitations, "mission-honesty"));
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }
  function renderCheckin() {
    const section = node("section", undefined, "card profile-detail"); section.id = "checkin";
    section.append(node("h2", "Daily check-in"), node("p", "Self-reports use a 1–5 scale. Enter only new measurements; leaving wearable fields empty preserves missing data.", "muted"));
    const form = node("form", undefined, "mission-checkin");
    const fields = [
      ["mission_day", "Mission day", "number", snapshot.latest_day + 1, snapshot.latest_day + 1, "1000000"],
      ["sleep_quality", "Sleep quality (1 very poor, 5 very good)", "number", 3, 1, 5],
      ["fatigue_score", "Fatigue (1 low, 5 high)", "number", 2, 1, 5],
      ["mood_score", "Mood (1 very poor, 5 very good)", "number", 4, 1, 5],
      ["workload_score", "Workload (1 low, 5 high)", "number", 3, 1, 5],
      ["resting_hr", "New resting heart rate, bpm (optional)", "number", "", 25, 220],
      ["sleep_hours", "New sleep duration, hours (optional)", "number", "", 0, 24],
    ];
    fields.forEach(([name, label, type, value, min, max]) => {
      const wrapper = node("label", label); const input = node("input"); Object.assign(input, { name, type, value, min, max, required: value !== "", step: value === "" ? "any" : "1" }); wrapper.append(input); form.append(wrapper);
    });
    const symptomsLabel = node("label", "Symptoms or notes (optional)"); const symptoms = node("textarea"); symptoms.name = "symptoms"; symptoms.maxLength = 2000; symptomsLabel.append(symptoms); form.append(symptomsLabel);
    const save = node("button", "Save check-in", "button button-primary"); save.type = "submit"; form.append(save);
    form.addEventListener("submit", async event => {
      event.preventDefault(); save.disabled = true;
      const values = Object.fromEntries(new FormData(form)); values.client_id = crypto.randomUUID();
      try {
        await queue(`/mission/astronaut/${snapshot.astronaut.id}/check-in/`, values);
        form.replaceChildren(node("p", "Check-in saved or queued. It will be assessed after delivery. Reload before entering another day."));
      } catch { say("Could not save this check-in to device storage. Please retry."); save.disabled = false; }
    });
    section.append(form); app.append(section);
  }
  document.getElementById("mission-sync").addEventListener("click", sync);
  simulate.addEventListener("change", () => { updateStatus(); if (!offline()) sync(); });
  window.addEventListener("online", () => { updateStatus(); sync(); });
  window.addEventListener("offline", updateStatus);
  async function start() {
    const source = document.getElementById("mission-snapshot");
    if (source) snapshot = JSON.parse(source.textContent);
    try {
      const cached = await storage("get", "snapshot");
      if (snapshot && cached && cached.owner !== snapshot.owner) await storage("delete", "snapshot");
      if (snapshot) await storage("put", "snapshot", snapshot);
      else snapshot = cached;
      outbox = snapshot ? await storage("get", `outbox-${snapshot.owner}`) || [] : [];
      lastSync = snapshot ? await storage("get", `lastSync-${snapshot.owner}`) : null;
    } catch { say("Device storage is unavailable. The online view works, but offline saves are unavailable."); }
    if (!snapshot) { say("No mission snapshot is saved on this device. Reconnect and open an astronaut overview first."); return; }
    render(); updateStatus();
    if (source) sync();
  }
  start();
})();
