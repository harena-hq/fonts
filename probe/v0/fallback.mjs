// SPDX-License-Identifier: Apache-2.0
// Which font does the browser actually draw a CJK string with, when the stack
// names only a Segoe family? Lays each string out in a span with a given `lang`
// and asks CDP (CSS.getPlatformFontsForNode) for the platform fonts used, plus
// the span's width at 1000 px.
//
// Usage: node probe/v0/fallback.mjs <cdp-http-base> <page-url> <strings.json> <family>
import { readFileSync } from 'node:fs';

const [base, pageUrl, stringsFile, family] = process.argv.slice(2);
const strings = JSON.parse(readFileSync(stringsFile, 'utf8'));
const target = await (await fetch(`${base}/json/new?about:blank`, { method: 'PUT' })).json();
const close = () => fetch(`${base}/json/close/${target.id}`).catch(() => {});
const timer = setTimeout(async () => { console.error('timeout'); await close(); process.exit(2); }, 600_000);
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
const send = (method, params = {}) => new Promise((ok) => {
  pending.set(++id, ok);
  ws.send(JSON.stringify({ id, method, params }));
});
const loaded = new Promise((ok) => waiters.push(function w(m) {
  if (m.method === 'Page.loadEventFired') ok(); else waiters.push(w);
}));

const out = [];
try {
await send('Page.enable');
await send('Page.navigate', { url: pageUrl });
await loaded;
await send('DOM.enable');
await send('CSS.enable');

const items = [];
for (const lang of ['en', 'ko', 'ja']) for (const [script, list] of Object.entries(strings))
  for (const s of list) items.push({ lang, script, s });
const built = await send('Runtime.evaluate', {
  expression: `(() => {
    const items = ${JSON.stringify(items)};
    items.forEach((it, i) => {
      const e = document.createElement('span');
      e.id = 'f' + i; e.lang = it.lang; e.textContent = it.s;
      e.style.cssText = ${JSON.stringify(`position:absolute;white-space:pre;font:400 1000px "${family}";`)};
      document.body.append(e);
    });
  })()`,
});
if (built.result?.exceptionDetails) throw new Error(JSON.stringify(built.result.exceptionDetails));
const { result: { root } } = await send('DOM.getDocument', { depth: -1 });
for (let i = 0; i < items.length; i++) {
  const { result: { nodeId } } = await send('DOM.querySelector', { nodeId: root.nodeId, selector: `#f${i}` });
  const res = await send('CSS.getPlatformFontsForNode', { nodeId });
  if (!res.result) throw new Error(JSON.stringify(res));
  const fonts = res.result.fonts;
  const w = (await send('Runtime.evaluate', {
    expression: `document.getElementById('f${i}').getBoundingClientRect().width`, returnByValue: true,
  })).result.result.value;
  out.push({ ...items[i], width: Math.round(w * 100) / 100,
             fonts: fonts.map((f) => `${f.familyName}${f.isCustomFont ? ' (web)' : ''}:${f.glyphCount}`) });
}
} finally {
  await close();
  clearTimeout(timer);
}
process.stdout.write(JSON.stringify(out) + '\n', () => process.exit(0));
