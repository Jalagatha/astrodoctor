const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('static/health/ui.js', 'utf8');

function element(extra = {}) {
  return Object.assign({ dataset: {}, listeners: {}, value: '', hidden: false,
    addEventListener(name, callback) { this.listeners[name] = callback; },
    setAttribute(name, value) { this[name] = value; },
  }, extra);
}
function boot({ saved = null, unavailable = false, cards = [], links = [], training = null } = {}) {
  let stored = saved;
  const controls = Object.fromEntries(['appearance-theme', 'appearance-background', 'connection-status'].map(id => [id, element()]));
  if (training) controls["training-dialog"] = training.dialog;
  const input = element();
  const count = element();
  const toolbar = element({ querySelector: selector => selector === 'input' ? input : count });
  const grid = cards.length ? {
    querySelector: () => cards[0], querySelectorAll: () => cards,
    before: () => {},
  } : null;
  const document = {
    documentElement: element(), body: element(),
    getElementById: id => controls[id],
    querySelector: selector => selector === "[data-open-training]" ? training?.opener : grid,
    querySelectorAll: selector => selector.startsWith('.main-nav') ? links : selector === 'form.training-form' && training ? [training.form] : [],
    createElement: () => toolbar,
  };
  const window = element();
  const navigator = { onLine: true };
  vm.runInNewContext(source, { document, window, navigator, location: { pathname: '/crew/3/' }, URL,
    localStorage: {
      getItem() { if (unavailable) throw Error('blocked'); return stored; },
      setItem(key, value) { if (unavailable) throw Error('blocked'); stored = value; },
    },
  });
  return { document, controls, window, navigator, input, count, get stored() { return stored; } };
}
test('preferences restore, change, and synchronize across tabs', () => {
  const ui = boot({ saved: JSON.stringify({ theme: 'dark', background: 'Waves' }) });
  assert.equal(ui.document.documentElement.dataset.theme, 'dark');
  assert.equal(ui.document.body.dataset.background, 'Waves');
  ui.controls['appearance-background'].value = 'Rosette';
  ui.controls['appearance-background'].listeners.change();
  assert.equal(JSON.parse(ui.stored).background, 'Rosette');
  ui.window.listeners.storage({ key: 'astrodoctor-ui-v1', newValue: '{"theme":"light","background":"Code"}' });
  assert.equal(ui.document.body.dataset.background, 'Code');
  assert.equal(ui.controls['appearance-theme'].value, 'light');
});
test('invalid and unavailable storage fall back without breaking the UI', () => {
  for (const settings of [{ saved: '{bad json' }, { unavailable: true }, { saved: '{"theme":"arbitrary","background":"../../bad"}' }]) {
    const ui = boot(settings);
    assert.equal(ui.document.documentElement.dataset.theme, 'dark');
    assert.equal(ui.document.body.dataset.background, 'Orbits');
    assert.match(ui.controls['connection-status'].textContent, /Online/);
  }
});
test('crew search filters cards and reports an empty result', () => {
  const cards = [element({ textContent: 'Amina Commander Artemis' }), element({ textContent: 'Sam Engineer Gateway' })];
  const ui = boot({ cards });
  ui.input.value = '  COMMANDER ';
  ui.input.listeners.input();
  assert.equal(cards[0].hidden, false);
  assert.equal(cards[1].hidden, true);
  assert.equal(ui.count.textContent, '1 of 2 crew members');
  ui.input.value = 'missing';
  ui.input.listeners.input();
  assert.equal(ui.count.textContent, '0 of 2 crew members');
});
test('connection state responds to offline and online events', () => {
  const ui = boot();
  ui.navigator.onLine = false;
  ui.window.listeners.offline();
  assert.match(ui.controls['connection-status'].textContent, /Offline/);
  ui.navigator.onLine = true;
  ui.window.listeners.online();
  assert.equal(ui.controls['connection-status'].dataset.online, 'true');
});
test('navigation marks the crew section active on nested pages', () => {
  const crew = element({ href: 'http://localhost/crew/' });
  const health = element({ href: 'http://localhost/' });
  boot({ links: [crew, health] });
  assert.equal(crew['aria-current'], 'page');
  assert.equal(health['aria-current'], undefined);
});

test('training modal opens, closes, updates split, and reports submission state', () => {
  const split = element({ value: '21', max: '35', validity: { valid: true } });
  const hint = element();
  const button = element();
  const status = element();
  const form = element({
    querySelector: selector => ({ '[name="baseline_rows"]': split, '#training-split': hint, '[type="submit"]': button, '[data-training-status]': status }[selector]),
    removeAttribute(name) { delete this[name]; },
  });
  const close = element();
  const dialog = element({ open: false, showModal() { this.open = true; }, close() { this.open = false; }, querySelector: () => close });
  const opener = element();
  boot({ training: { dialog, opener, form } });
  let prevented = false;
  opener.listeners.click({ preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(dialog.open, true);
  close.listeners.click();
  assert.equal(dialog.open, false);
  split.value = '28';
  split.listeners.input();
  assert.match(hint.textContent, /28 baseline rows · 14 later evaluation rows/);
  form.listeners.submit();
  assert.equal(button.disabled, true);
  assert.equal(form['aria-busy'], 'true');
  assert.match(status.textContent, /Fitting baseline/);
});
