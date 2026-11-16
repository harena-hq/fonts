// Evaluated in the probe page. CONFIG = { font, family, weight, small, px, cases: [{text, css, lang}] }.
// Item 4: one built J face, served as a web font declared at exactly its weight, against the
// Segoe face `family` at `weight`, in DOM layout. Compared here, so only what is outside the
// tolerance comes back: 0.1% of Windows' width, or for a Small face within one layout unit.
// Returns {sha256 (of the bytes loaded), count, unit, over: [[what, ours, theirs]]}. A J face is
// too large to send back as v0.3's check does, and the page is not a secure context, so it is
// hashed here.
(async () => {
  const sha256 = (bytes) => {
    const k = [], h = [];
    for (let n = 2, found = 0; found < 64; n++) {
      let prime = true;
      for (let d = 2; d * d <= n; d++) if (n % d === 0) { prime = false; break; }
      if (!prime) continue;
      if (found < 8) h.push((Math.sqrt(n) % 1) * 2 ** 32 | 0);
      k.push((Math.cbrt(n) % 1) * 2 ** 32 | 0);
      found++;
    }
    const length = bytes.length, padded = new Uint8Array(((length + 9 + 63) >> 6) << 6);
    padded.set(bytes);
    padded[length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(padded.length - 8, Math.floor(length / 2 ** 29));
    view.setUint32(padded.length - 4, (length << 3) >>> 0);
    const w = new Int32Array(64), rotr = (x, n) => (x >>> n) | (x << (32 - n));
    for (let i = 0; i < padded.length; i += 64) {
      for (let t = 0; t < 16; t++) w[t] = view.getInt32(i + 4 * t);
      for (let t = 16; t < 64; t++) {
        const a = w[t - 15], b = w[t - 2];
        w[t] = (w[t - 16] + (rotr(a, 7) ^ rotr(a, 18) ^ (a >>> 3)) + w[t - 7]
                + (rotr(b, 17) ^ rotr(b, 19) ^ (b >>> 10))) | 0;
      }
      let [a, b, c, d, e, f, g, x] = h;
      for (let t = 0; t < 64; t++) {
        const t1 = (x + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k[t] + w[t]) | 0;
        const t2 = ((rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
        x = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
      }
      [a, b, c, d, e, f, g, x].forEach((v, n) => { h[n] = (h[n] + v) | 0; });
    }
    return h.map((v) => (v >>> 0).toString(16).padStart(8, '0')).join('');
  };
  const w = CONFIG.weight, px = CONFIG.px;
  const bytes = await (await fetch(CONFIG.font)).arrayBuffer();
  const face = new FontFace('Harena UI Check', bytes, { weight: String(w) });
  document.fonts.add(await face.load());
  await document.fonts.load(`${w} 100px "${CONFIG.family}"`);
  const span = document.createElement('span');
  document.body.append(span);
  const dom = (fam, text, css, lang) => {
    if (lang) span.lang = lang; else span.removeAttribute('lang');
    span.style.cssText = `position:absolute;white-space:pre;font-family:"${fam}";font-weight:${w};` +
      `font-size:${px}px;${css || ''}`;
    span.textContent = text;
    return span.getBoundingClientRect().width * 1000 / px;
  };
  const out = { sha256: sha256(new Uint8Array(bytes)), count: 0, unit: 0, rounded: 0, over: [] };
  // What a character Windows emboldens gains at this size: a whole pixel over 1019.53 units
  const pixel = (Math.ceil(1.01953125 * px) - 1.01953125 * px) * 1000 / px;
  for (const c of CONFIG.cases) {
    const ours = dom('Harena UI Check', c.text, c.css, c.lang);
    const theirs = dom(CONFIG.family, c.text, c.css, c.lang);
    out.count++;
    if (Math.abs(ours - theirs) <= 0.001 * theirs) continue;
    if (CONFIG.small && Math.abs(ours - theirs) * px / 1000 <= 1 / 64 + 1e-9) { out.unit++; continue; }
    let whole = false;
    for (let n = 1; n <= (c.bold || 0); n++) {
      if (Math.abs(theirs - ours - n * pixel) * px / 1000 <= 1 / 32) whole = true;
    }
    if (whole) { out.rounded++; continue; }
    out.over.push([`${px} px ${c.css || ''} lang=${c.lang || '-'} ${JSON.stringify(c.text)}`, ours, theirs]);
  }
  return out;
})()
