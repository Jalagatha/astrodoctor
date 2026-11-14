(() => {
  "use strict";
  document.querySelectorAll('form.profile-form input[type="file"][name="photo"]').forEach((input) => {
    const form = input.form;
    const controls = document.createElement("div");
    controls.className = "camera-controls";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "button button-secondary";
    open.textContent = "Take a photo";
    const status = document.createElement("p");
    status.className = "form-status";
    status.setAttribute("role", "status");
    controls.append(open, status);
    input.after(controls);

    const dialog = document.createElement("dialog");
    dialog.className = "camera-dialog";
    dialog.setAttribute("aria-label", "Take a profile photo");
    dialog.innerHTML = '<h2>Take your profile photo</h2><p>Position yourself in the frame, then capture.</p><video autoplay playsinline muted></video><div class="checkin-actions"><button type="button" class="button button-primary" data-capture disabled>Capture photo</button><button type="button" class="button button-secondary" data-cancel>Cancel</button></div>';
    document.body.append(dialog);
    const video = dialog.querySelector("video");
    const capture = dialog.querySelector("[data-capture]");
    let stream = null;
    let generation = 0;
    function stop() {
      generation += 1;
      if (stream) stream.getTracks().forEach((track) => track.stop());
      stream = null;
      video.srcObject = null;
      capture.disabled = true;
    }
    const close = () => { stop(); if (dialog.open) dialog.close(); };
    dialog.querySelector("[data-cancel]").addEventListener("click", close);
    dialog.addEventListener("close", stop);
    dialog.addEventListener("cancel", stop);
    window.addEventListener("pagehide", close);
    document.addEventListener("visibilitychange", () => { if (document.hidden) close(); });
    form.addEventListener("submit", close);
    video.addEventListener("loadedmetadata", () => { capture.disabled = !stream || !video.videoWidth; });
    open.addEventListener("click", async () => {
      status.textContent = "";
      if (!navigator.mediaDevices?.getUserMedia || !dialog.showModal) {
        status.textContent = "Camera access is unavailable here. Use the file picker to choose a photo; supported mobile devices can also open their camera.";
        return;
      }
      if (dialog.open) return;
      dialog.showModal();
      const requestGeneration = ++generation;
      try {
        const camera = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 800 }, height: { ideal: 800 } }, audio: false });
        if (generation !== requestGeneration || !dialog.open) {
          camera.getTracks().forEach((track) => track.stop());
          return;
        }
        stream = camera;
        video.srcObject = camera;
        await video.play();
        if (generation === requestGeneration && dialog.open) capture.disabled = !video.videoWidth;
      } catch (error) {
        if (generation !== requestGeneration) return;
        close();
        status.textContent = error.name === "NotAllowedError"
          ? "Camera permission was declined. You can allow it in your browser settings or upload a file."
          : "Could not open your camera. Check that it is connected and available, or upload a file.";
      }
    });
    capture.addEventListener("click", () => {
      if (!stream || !video.videoWidth) return;
      capture.disabled = true;
      const canvas = document.createElement("canvas");
      const scale = Math.min(800 / video.videoWidth, 800 / video.videoHeight, 1);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (!dialog.open) return;
        if (!blob) { capture.disabled = false; return; }
        try {
          const files = new DataTransfer();
          files.items.add(new File([blob], "camera-portrait.jpg", { type: "image/jpeg" }));
          input.files = files.files;
          input.dispatchEvent(new Event("change", { bubbles: true }));
          status.textContent = "Photo captured. Save your profile to keep it, or choose another photo.";
        } catch {
          status.textContent = "This browser could not attach the photo. Please use the file upload instead.";
        }
        close();
      }, "image/jpeg", .9);
    });
  });
})();
