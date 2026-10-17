const { JSDOM } = require('jsdom');
const fs = require('fs');
const html = fs.readFileSync(__dirname + '/../app/artifact.html', 'utf8');
// emulate publish skeleton
const page = '<!doctype html><html><head><meta charset=utf8></head><body>' + html + '</body></html>';
const store = {}; const writes = [];
const fakeDoc = (path) => ({
  get: async () => ({ exists: path in store, data: () => store[path] }),
  set: async (d) => { writes.push(JSON.parse(JSON.stringify(d))); store[path] = JSON.parse(JSON.stringify(d)); },
  onSnapshot: () => () => {},
});
const dom = new JSDOM(page, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.test/',
  beforeParse(w) {
    w.matchMedia = () => ({ matches: true });
    w.claude = { use: async (n) => n === 'db' ? { doc: fakeDoc } : n === 'user' ? { id: async () => 'u_test' } : null };
  } });
const w = dom.window, d = w.document;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const q = (id) => d.getElementById(id);
(async () => {
  await sleep(50);
  const log = (...a) => console.log(...a);
  log('sync:', q('sync').textContent, '| front word:', q('fWord').textContent, '| chips:', [...d.querySelectorAll('.chip')].map(c => c.textContent).join(' '));
  log('stats:', q('nKnown').textContent, q('nNew').textContent, q('nUnseen').textContent, '| left:', q('left').textContent);
  q('card').click(); log('flipped:', q('card').dataset.flipped, '| EN:', q('bEn').textContent, '| RU:', q('bRu').textContent, '| mark:', q('fEx').querySelector('mark')?.textContent, '| answer:', q('bAnsBadge').textContent);
  const w1 = q('fWord').textContent;
  q('bKnow').click(); await sleep(700);
  log('after KNOW of', w1, '-> known', q('nKnown').textContent, 'new word:', q('fWord').textContent, 'flipped', q('card').dataset.flipped);
  const w2 = q('fWord').textContent;
  q('bNew').click(); await sleep(700);
  log('after NEW of', w2, '-> marked new', q('nNew').textContent, 'unseen', q('nUnseen').textContent);
  q('undo').click(); await sleep(50);
  log('undo -> current', q('fWord').textContent, '(expected', w2 + ') marked new', q('nNew').textContent);
  // exclusion: mark known 300 times; known words must never reappear
  const known = new Set([w1]); let dupes = 0, newSeenAgain = 0; const newSet = new Set();
  for (let i = 0; i < 300; i++) {
    const cur = q('fWord').textContent; if (known.has(cur)) dupes++;
    if (i % 3 === 0) { q('bNew').click(); newSet.add(cur); } else { q('bKnow').click(); known.add(cur); }
    if (i % 50 === 0) await sleep(5);
  }
  log('300 actions: known-shown-again =', dupes, '| known', q('nKnown').textContent, '| marked new', q('nNew').textContent);
  // new words reappear?
  let seenNew = 0; for (let i = 0; i < 400; i++) { const c = q('fWord').textContent; if (newSet.has(c)) seenNew++; q('bNew').click(); }
  log('new words reappear in later draws:', seenNew > 0, seenNew);
  // levels
  [...d.querySelectorAll('.chip')].forEach(c => { if (/^[BCD] /.test(c.textContent)) c.click(); });
  log('only A selected; pressed:', [...d.querySelectorAll('.chip')].map(c => c.getAttribute('aria-pressed')).join(','));
  const lastChip = d.getElementById('chipA'); lastChip.click(); log('cannot deselect last level ->', lastChip.getAttribute('aria-pressed'));
  await sleep(700);
  log('writes to db:', writes.length, '| last write keys:', Object.keys(writes.at(-1)), 'known', writes.at(-1).known.length, 'learning', writes.at(-1).learning.length, '| sync:', q('sync').textContent);
  // reload: new window with the same store should restore
  const dom2 = new JSDOM(page, { runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.test/',
    beforeParse(w2) { w2.matchMedia = () => ({ matches: true }); w2.claude = { use: async (n) => n === 'db' ? { doc: fakeDoc } : n === 'user' ? { id: async () => 'u_test' } : null }; } });
  await sleep(100);
  const d2 = dom2.window.document;
  log('reload restored known =', d2.getElementById('nKnown').textContent, '| levels pressed', [...d2.querySelectorAll('.chip')].map(c => c.getAttribute('aria-pressed')).join(','), '| sync:', d2.getElementById('sync').textContent);
  // finish deck: level A only, mark everything known
  for (let i = 0; i < 100 && !q('done').hidden === false; i++) {}
  let guard = 0; while (q('done').hidden && guard++ < 200) q('bKnow').click();
  log('deck finished screen shown:', !q('done').hidden, '| scene hidden:', q('scene').hidden, '| buttons disabled:', q('bKnow').disabled);
  process.exit(0);
})();
