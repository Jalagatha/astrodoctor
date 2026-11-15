// Countdown for the VR session player. The server records the real duration when
// the session ends; this script only shows the time remaining and the progress ring.
(() => {
  const player = document.querySelector("[data-session-timer]");
  if (!player) return;
  const display = player.querySelector("[data-timer-display]");
  const ring = player.querySelector("[data-timer-ring]");
  const note = player.querySelector("[data-timer-note]");
  const button = player.querySelector("[data-timer-end]");
  const total = Number(player.dataset.total) * 60;
  const endsAt = Date.now() + Number(player.dataset.remaining) * 1000;

  function render() {
    const remaining = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
    display.textContent = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}`;
    if (ring) ring.style.strokeDashoffset = String(total ? (remaining / total) * 100 : 0);
    if (remaining === 0) {
      note.textContent = "Session complete. Take off your headset when you are ready.";
      button.textContent = "Continue to re-check →";
      player.dispatchEvent(new CustomEvent("session:complete"));
      return;
    }
    setTimeout(render, 1000);
  }
  render();

  // Full-screen toggle for the session stage.
  const fullscreen = player.querySelector("[data-fullscreen]");
  if (fullscreen) {
    if (!player.requestFullscreen) fullscreen.hidden = true;
    fullscreen.addEventListener("click", () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else player.requestFullscreen().catch(() => {});
    });
  }
})();
