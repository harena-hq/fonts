// SPDX-License-Identifier: Apache-2.0
// Open a page on a remote browser over CDP, wait for its fonts, and save a
// full-page PNG at device scale 1.
//
// Usage: node probe/shot.mjs <cdp-http-base> <page-url> <out.png> [width]
import { writeFileSync } from 'node:fs';

const [base, pageUrl, outFile, width = '1500'] = process.argv.slice(2);
const target = await (await fetch(`${base}/json/new?about:blank`, { method: 'PUT' })).json();
const close = () => fetch(`${base}/json/close/${target.id}`).catch(() => {});
const timer = setTimeout(async () => { console.error('timeout'); await close(); process.exit(2); }, 120_000);
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

try {
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: +width, height: 1000, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: pageUrl });
await loaded;
await send('Runtime.evaluate', { expression: 'document.fonts.ready.then(() => 0)', awaitPromise: true });
const { result: { cssContentSize } } = await send('Page.getLayoutMetrics');
const shot = await send('Page.captureScreenshot', {
  format: 'png', captureBeyondViewport: true,
  clip: { x: 0, y: 0, width: +width, height: Math.ceil(cssContentSize.height), scale: 1 },
});
writeFileSync(outFile, Buffer.from(shot.result.data, 'base64'));
} finally {
  await close();
  clearTimeout(timer);
}
process.exit(0);
