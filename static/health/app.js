(() => {
  const form = document.getElementById("checkin-form");
  const status = document.getElementById("checkin-status");
  const DB_NAME = "astrodoctor-offline";
  const STORE = "checkins";

  function openQueue() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "client_id" });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function queue(action, value) {
    const db = await openQueue();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE, action === "getAll" ? "readonly" : "readwrite");
      const request = action === "getAll" ? transaction.objectStore(STORE).getAll() : transaction.objectStore(STORE)[action](value);
      let result;
      request.onsuccess = () => { result = request.result; };
      transaction.oncomplete = () => { db.close(); resolve(result); };
      transaction.onerror = () => { db.close(); reject(transaction.error); };
      transaction.onabort = () => { db.close(); reject(transaction.error || new Error("Storage transaction aborted.")); };
    });
  }

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  async function deliver(item, endpoint) {
    const response = await fetch(endpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(item),
    });
    if (response.redirected) {
      const error = new Error("Sign in again to sync this check-in.");
      error.needsLogin = true;
      throw error;
    }
    if (!response.headers.get("content-type")?.includes("application/json")) {
      throw new Error(`The server returned an unexpected response (${response.status}).`);
    }
    const result = await response.json();
    if (!response.ok) {
      const error = new Error(result.error || "Check-in could not be saved.");
      error.rejected = response.status === 400;
      throw error;
    }
    await queue("delete", item.client_id);
    return result;
  }

  let syncing = false;

  async function syncPending(endpoint) {
    if (!navigator.onLine || syncing) return;
    syncing = true;
    try {
      let items;
      try {
        items = await queue("getAll");
      } catch (error) {
        return;
      }
      items.sort((a, b) => (a.queued_at || 0) - (b.queued_at || 0));
      for (const item of items) {
        try {
          const result = await deliver(item, endpoint);
          if (status) {
            status.textContent = `Offline check-in synced for mission day ${result.day}.`;
            status.classList.remove("error");
          }
        } catch (error) {
          if (status && error.needsLogin) {
            status.textContent = "Reconnect and sign in to sync your saved check-in.";
          } else if (status && error instanceof TypeError) {
            status.textContent = "Connection lost. Your saved check-in is waiting to sync.";
          } else if (status) {
            status.textContent = error.message;
            status.classList.add("error");
          }
          break;
        }
      }
    } finally {
      syncing = false;
    }
  }

  if (form) {
    const endpoint = form.dataset.endpoint;
    form.querySelectorAll('input[type="range"]').forEach((input) => {
      const output = input.parentElement.querySelector("output");
      input.addEventListener("input", () => { output.value = input.value; });
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = form.querySelector('[type="submit"]');
      if (submit.disabled) return;
      submit.disabled = true;
      const data = new FormData(form);
      const item = {
        client_id: crypto.randomUUID(),
        queued_at: Date.now(),
        mood: Number(data.get("mood")),
        stress: Number(data.get("stress")),
        sleep_h: Number(data.get("sleep_h")),
        symptoms: data.getAll("symptoms"),
      };
      let stored = false;
      try {
        await queue("put", item);
        stored = true;
        if (!navigator.onLine) throw new TypeError("offline");
        const result = await deliver(item, endpoint);
        status.textContent = result.message;
        status.classList.remove("error");
        form.reset();
        form.querySelectorAll('input[type="range"]').forEach((input) => {
          const output = input.parentElement.querySelector("output");
          if (output) output.value = input.value;
        });
        if (!location.pathname.endsWith("/offline/")) location.reload();
      } catch (error) {
        if (error instanceof TypeError || error.needsLogin) {
          try {
            await queue("put", item);
            status.textContent = error.needsLogin
              ? "Saved on this device. Sign in again to sync."
              : "Saved on this device. It will sync when you're online and signed in.";
            status.classList.remove("error");
            form.reset();
          } catch (storageError) {
            status.textContent = "Could not save this check-in on the device. Please retry.";
            status.classList.add("error");
          }
        } else {
          if (stored && error.rejected) await queue("delete", item.client_id);
          status.textContent = stored && !error.rejected
            ? `${error.message} Saved on this device for retry.`
            : error.message;
          status.classList.add("error");
        }
      } finally {
        submit.disabled = false;
        form.querySelectorAll('input[type="range"]').forEach((input) => {
          const output = input.parentElement.querySelector("output");
          if (output) output.value = input.value;
        });
      }
    });
    syncPending(endpoint);
    window.addEventListener("online", () => syncPending(endpoint));
  }

  const svg = document.getElementById("trend-chart");
  const dataNode = document.getElementById("chart-data");
  if (svg && dataNode) {
    const rows = JSON.parse(dataNode.textContent);
    if (rows.length) {
      const width = 680;
      const height = 225;
      const pad = { top: 16, right: 12, bottom: 26, left: 34 };
      const values = rows.map((row) => row.value);
      const baseline = rows[0].baseline;
      const span = Math.max(...values, baseline) - Math.min(...values, baseline) || 1;
      const min = Math.min(...values, baseline) - span * .12;
      const max = Math.max(...values, baseline) + span * .12;
      const x = (index) => pad.left + index * (width - pad.left - pad.right) / Math.max(rows.length - 1, 1);
      const y = (value) => pad.top + (max - value) * (height - pad.top - pad.bottom) / (max - min);
      const points = rows.map((row, index) => `${x(index)},${y(row.value)}`).join(" ");
      const grid = [0, 1, 2, 3].map((step) => {
        const gy = pad.top + step * (height - pad.top - pad.bottom) / 3;
        const label = (max - step * (max - min) / 3).toFixed(1);
        return `<line class="chart-grid" x1="${pad.left}" y1="${gy}" x2="${width - pad.right}" y2="${gy}"/><text class="chart-label" x="0" y="${gy + 3}">${label}</text>`;
      }).join("");
      const baseY = y(baseline);
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      svg.innerHTML = `${grid}<line class="chart-baseline" x1="${pad.left}" y1="${baseY}" x2="${width - pad.right}" y2="${baseY}"/><polyline class="chart-value" points="${points}"/><text class="chart-label" x="${pad.left}" y="${height - 5}">Day ${rows[0].day}</text><text class="chart-label" text-anchor="end" x="${width - pad.right}" y="${height - 5}">Day ${rows[rows.length - 1].day}</text>`;
    }
  }
})();
