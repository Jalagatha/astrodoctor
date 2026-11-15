// Ambient soundscape for the VR session player.
//
// * Gapless looping and smooth fades via the Web Audio API.
// * The loop starts at the same point in the 10 s breathing cycle as the 3D scene
//   (both read performance.now()), so the sound's swell matches the visual guide.
// * Sound on/off and volume are remembered on this device only (localStorage).
// * Browsers may block sound until the viewer interacts; we then show a
//   "Tap for sound" button instead of failing silently.
(() => {
  "use strict";
  const stage = document.querySelector("[data-ambience]");
  if (!stage) return;
  const toggle = stage.querySelector("[data-sound-toggle]");
  const volume = stage.querySelector("[data-sound-volume]");
  const prompt = stage.querySelector("[data-sound-prompt]");
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass || !window.fetch) {
    stage.querySelectorAll("[data-sound-control]").forEach((node) => { node.hidden = true; });
    return;
  }

  const KEY = "astrodoctor-sound-v1";
  let prefs = { on: true, volume: 0.7 };
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    if (typeof saved.on === "boolean") prefs.on = saved.on;
    if (Number.isFinite(saved.volume)) prefs.volume = Math.min(1, Math.max(0, saved.volume));
  } catch { /* storage unavailable: defaults apply for this visit */ }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch { /* ignore */ } };

  let context = null;
  let gain = null;
  let source = null;
  let buffer = null;
  let loading = null;
  let finished = false;

  function createContext() {
    if (context) return;
    context = new AudioContextClass();
    gain = context.createGain();
    gain.gain.value = 0;
    gain.connect(context.destination);
  }

  function load() {
    loading ||= fetch(stage.dataset.ambience)
      .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.arrayBuffer(); })
      .then((data) => new Promise((resolve, reject) => context.decodeAudioData(data, resolve, reject)))
      .then((decoded) => { buffer = decoded; return decoded; });
    return loading;
  }

  function ramp(target, seconds) {
    if (!context) return;
    const now = context.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(gain.gain.value, now);
    gain.gain.linearRampToValueAtTime(target, now + seconds);
  }

  async function resume() {
    if (context.state === "running") return true;
    // resume() can stay pending without a user gesture; don't wait on it forever.
    await Promise.race([context.resume().catch(() => {}), new Promise((resolve) => setTimeout(resolve, 400))]);
    return context.state === "running";
  }

  async function play() {
    if (finished) return;
    try {
      createContext();
      const loaded = load(); // download and decode in the background…
      const allowed = await resume(); // …while finding out whether the browser allows sound
      prompt.hidden = allowed;
      await loaded;
      if (!allowed || finished || !prefs.on) return;
      if (!source) {
        source = context.createBufferSource();
        source.buffer = buffer;
        source.loop = true;
        source.connect(gain);
        source.start(0, (performance.now() / 1000) % buffer.duration);
      }
      ramp(prefs.volume, 2.5);
    } catch (error) {
      console.warn("Soundscape unavailable.", error);
      stage.querySelectorAll("[data-sound-control]").forEach((node) => { node.hidden = true; });
      prompt.hidden = true;
    }
  }

  function render() {
    toggle.classList.toggle("is-muted", !prefs.on);
    toggle.setAttribute("aria-pressed", String(prefs.on));
    toggle.setAttribute("aria-label", prefs.on ? "Turn sound off" : "Turn sound on");
    toggle.title = prefs.on ? "Sound on" : "Sound off";
    volume.value = String(prefs.volume);
    volume.disabled = !prefs.on;
  }

  toggle.addEventListener("click", () => {
    prefs.on = !prefs.on;
    save();
    render();
    if (prefs.on) play();
    else { ramp(0, 0.8); prompt.hidden = true; }
  });
  volume.addEventListener("input", () => {
    prefs.volume = Number(volume.value);
    save();
    if (prefs.on && context) ramp(prefs.volume, 0.15);
  });
  prompt.addEventListener("click", () => { prefs.on = true; save(); render(); play(); });
  // Any interaction with the stage unlocks audio if the browser blocked autoplay.
  stage.addEventListener("pointerdown", () => { if (prefs.on && !prompt.hidden) play(); });

  // Fade out gently when the session timer completes.
  stage.addEventListener("session:complete", () => { finished = true; ramp(0, 8); });
  document.addEventListener("visibilitychange", () => {
    if (!context) return;
    if (document.hidden) context.suspend();
    else if (prefs.on && !finished) context.resume();
  });
  window.addEventListener("pagehide", () => { if (context) context.close(); });

  render();
  if (prefs.on) play();
})();
