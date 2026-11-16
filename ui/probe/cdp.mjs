// SPDX-License-Identifier: Apache-2.0
// Open a page on a remote browser over CDP, evaluate one expression in it, and
// print the value as JSON. Exits on its own: CDP clients otherwise hang on exit.
//
// Usage: node probe/cdp.mjs <cdp-http-base> <page-url> <expression-file> [timeout-seconds] [device-scale-factor]
// A device scale factor lays the page out as on a display at that scale (Windows' 200%: 2).
import { readFileSync } from 'node:fs';

const [base, pageUrl, exprFile, seconds = '600', scale] = process.argv.slice(2);
const expression = readFileSync(exprFile, 'utf8');
const target = await (await fetch(`${base}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' })).json();
const close = () => fetch(`${base}/json/close/${target.id}`).catch(() => {});
const timer = setTimeout(async () => { console.error('timeout'); await close(); process.exit(2); }, +seconds * 1000);
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
const event = (name) => new Promise(function wait(ok) {
  waiters.push((m) => (m.method === name ? ok(m) : wait(ok)));
});

let res;
try {
  await send('Page.enable');
  // a page lays out the files it fetches now, never ones an earlier run left in the cache
  await send('Network.enable');
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  if (scale) {
    await send('Emulation.setDeviceMetricsOverride', { width: 0, height: 0, deviceScaleFactor: +scale, mobile: false });
  }
  const loaded = event('Page.loadEventFired');
  await send('Page.navigate', { url: pageUrl });
  await loaded;
  res = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
} finally {
  await close();
  clearTimeout(timer);
}
if (res.result?.exceptionDetails) {
  console.error(JSON.stringify(res.result.exceptionDetails, null, 1));
  process.exit(1);
}
// process.exit() does not wait for a piped stdout to drain, and would cut the
// output at the pipe buffer (64 KiB).
process.stdout.write(JSON.stringify(res.result.result.value) + '\n', () => process.exit(0));
