const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('static/health/camera.js', 'utf8');
function element(extra = {}) {
  return Object.assign({ listeners: {}, children: [],
    addEventListener(event, fn) { this.listeners[event] = fn; },
    setAttribute() {}, append(...children) { this.children.push(...children); },
    after() {},
  }, extra);
}
function setup(getUserMedia) {
  let stopped = 0;
  const track = { stop() { stopped += 1; } };
  const stream = { getTracks: () => [track] };
  const form = element();
  const input = element({ form });
  const controls = element();
  const open = element();
  const status = element();
  const capture = element({ disabled: true });
  const cancel = element();
  const video = element({ videoWidth: 800, videoHeight: 600, play: async () => {} });
  const dialog = element({ open: false,
    showModal() { this.open = true; }, close() { this.open = false; this.listeners.close(); },
    querySelector(selector) { return { video, '[data-capture]': capture, '[data-cancel]': cancel }[selector]; },
  });
  const elements = [controls, open, status, dialog];
  const document = element({
    body: element(),
    querySelectorAll: () => [input], createElement: () => elements.shift(),
  });
  const window = element();
  vm.runInNewContext(source, { document, window, navigator: { mediaDevices: { getUserMedia: () => getUserMedia(stream) } } });
  return { open, status, dialog, cancel, video, capture, window, form, document, get stopped() { return stopped; } };
}
test('camera opens only on request and stops on cancel', async () => {
  let calls = 0;
  const ui = setup(async stream => { calls++; return stream; });
  assert.equal(calls, 0);
  await ui.open.listeners.click();
  assert.equal(ui.dialog.open, true);
  assert.equal(ui.capture.disabled, false);
  ui.cancel.listeners.click();
  assert.equal(ui.dialog.open, false);
  assert.equal(ui.stopped, 1);
});
test('permission denial offers upload fallback', async () => {
  const ui = setup(async () => { throw Object.assign(new Error(), { name: 'NotAllowedError' }); });
  await ui.open.listeners.click();
  assert.equal(ui.dialog.open, false);
  assert.match(ui.status.textContent, /declined.*upload/);
});
test('camera tracks returned after cancellation are immediately stopped', async () => {
  let resolve;
  const ui = setup(stream => new Promise(done => { resolve = () => done(stream); }));
  const opening = ui.open.listeners.click();
  ui.cancel.listeners.click();
  resolve();
  await opening;
  assert.equal(ui.stopped, 1);
  assert.equal(ui.video.srcObject, null);
});
test('camera stops when page is hidden', async () => {
  const ui = setup(async stream => stream);
  await ui.open.listeners.click();
  ui.document.hidden = true;
  ui.document.listeners.visibilitychange();
  assert.equal(ui.stopped, 1);
  assert.equal(ui.dialog.open, false);
});
