// SPDX-License-Identifier: Apache-2.0
// Which installed faces Edge draws a text with, by name and glyph count, as DevTools reports them.
// CONFIG (JSON file) = { cases: [{ key, family, weight, lang, text }] }; prints { key: [[family,
// postScriptName, glyphs], ...] }. Only names and counts leave the machine.
//
// Usage: node probe/v0_6/fallback.mjs <cdp-http-base> <page-url> <config.json>
import { readFileSync } from 'node:fs';

const [base, pageUrl, configFile] = process.argv.slice(2);
const { cases } = JSON.parse(readFileSync(configFile, 'utf8'));
const target = await (await fetch(`${base}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' })).json();
const close = () => fetch(`${base}/json/close/${target.id}`).catch(() => {});
const timer = setTimeout(async () => { console.error('timeout'); await close(); process.exit(2); }, 3600 * 1000);
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((ok, fail) => { ws.onopen = ok; ws.onerror = fail; });

let id = 0;
const pending = new Map();
const waiters = [];
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  else for (const w of waiters.splice(0)) w(msg);
};
const send = (method, params = {}) => new Promise((ok, fail) => {
  pending.set(++id, (m) => (m.error ? fail(new Error(`${method}: ${m.error.message}`)) : ok(m.result)));
  ws.send(JSON.stringify({ id, method, params }));
});
const event = (name) => new Promise(function wait(ok) {
  waiters.push((m) => (m.method === name ? ok(m) : wait(ok)));
});

const out = {};
try {
  await send('Page.enable');
  const loaded = event('Page.loadEventFired');
  await send('Page.navigate', { url: pageUrl });
  await loaded;
  await send('DOM.enable');
  await send('CSS.enable');
  const { root } = await send('DOM.getDocument', { depth: 0 });
  for (const c of cases) {
    await send('Runtime.evaluate', {
      expression: `(() => { document.body.innerHTML = ''; const d = document.createElement('div');
        d.id = 'probe'; ${c.lang ? `d.lang = ${JSON.stringify(c.lang)};` : ''}
        d.style.cssText = ${JSON.stringify(`font-family:${c.family};font-weight:${c.weight};font-size:16px;white-space:pre`)};
        d.textContent = ${JSON.stringify(c.text)}; document.body.append(d); return d.offsetWidth; })()`,
      returnByValue: true,
    });
    const { nodeId } = await send('DOM.querySelector', { nodeId: root.nodeId, selector: '#probe' });
    const { fonts } = await send('CSS.getPlatformFontsForNode', { nodeId });
    out[c.key] = fonts.map((f) => [f.familyName, f.postScriptName, f.glyphCount]);
  }
} finally {
  await close();
  clearTimeout(timer);
}
process.stdout.write(JSON.stringify(out) + '\n', () => process.exit(0));
