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
function boot({ saved = null, unavailable = false, cards = [], links = [] } = {}) {
  let stored = saved;
  const controls = Object.fromEntries(['appearance-theme', 'connection-status'].map(id => [id, element()]));
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
    querySelector: () => grid,
    querySelectorAll: selector => selector.startsWith('.main-nav') ? links : [],
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
test('theme preference restores, changes, and synchronizes across tabs', () => {
  const ui = boot({ saved: JSON.stringify({ theme: 'light', background: 'Waves' }) });
  assert.equal(ui.document.documentElement.dataset.theme, 'light');
  assert.deepEqual(JSON.parse(ui.stored), { theme: 'light' });  // old backdrop setting is dropped
  ui.controls['appearance-theme'].value = 'dark';
  ui.controls['appearance-theme'].listeners.change();
  assert.equal(JSON.parse(ui.stored).theme, 'dark');
  ui.window.listeners.storage({ key: 'astrodoctor-ui-v1', newValue: '{"theme":"light"}' });
  assert.equal(ui.document.documentElement.dataset.theme, 'light');
  assert.equal(ui.controls['appearance-theme'].value, 'light');
  ui.window.listeners.storage({ key: 'astrodoctor-ui-v1', newValue: '{"theme":"neon"}' });
  assert.equal(ui.document.documentElement.dataset.theme, 'light');
});
test('invalid and unavailable storage fall back without breaking the UI', () => {
  for (const settings of [{ saved: '{bad json' }, { unavailable: true }, { saved: '{"theme":"arbitrary"}' }]) {
    const ui = boot(settings);
    assert.equal(ui.document.documentElement.dataset.theme, 'dark');
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
