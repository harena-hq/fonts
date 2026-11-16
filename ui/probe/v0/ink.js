// Evaluated in the probe page. CONFIG = { families: [[name, weight], ...], glyphs: [cp, ...] }.
// Ink box from pixels, because measureText's actualBoundingBox* are rounded
// outward to 1/64 em. Each glyph is drawn at 1000 px; an edge is the outermost
// row or column with any coverage, refined by that line's peak coverage
// (a line covered to 0.3 contributes 0.3 px). Values are px from the origin,
// y up: [left, right, top, bottom].
(async () => {
  for (const [fam, w] of CONFIG.families) await document.fonts.load(`${w} 100px "${fam}"`);
  const PX = 1000, W = 2400, H = 2000, X0 = 700, BASE = 1400;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d', { willReadFrequently: true });
  const r2 = (x) => Math.round(x * 100) / 100;
  const out = {};
  for (const [fam, w] of CONFIG.families) {
    g.font = `${w} ${PX}px "${fam}"`;
    const rows = {};
    for (const cp of CONFIG.glyphs) {
      const ch = String.fromCodePoint(cp);
      const m = g.measureText(ch);
      // The rounded box bounds the search; widen it by a grid step each way.
      const x0 = Math.max(0, Math.floor(X0 - m.actualBoundingBoxLeft) - 20);
      const x1 = Math.min(W, Math.ceil(X0 + m.actualBoundingBoxRight) + 20);
      const y0 = Math.max(0, Math.floor(BASE - m.actualBoundingBoxAscent) - 20);
      const y1 = Math.min(H, Math.ceil(BASE + m.actualBoundingBoxDescent) + 20);
      if (x1 <= x0 || y1 <= y0) { rows[cp] = null; continue; }
      g.clearRect(0, 0, W, H); g.fillStyle = '#000'; g.fillText(ch, X0, BASE);
      const bw = x1 - x0, bh = y1 - y0;
      const d = g.getImageData(x0, y0, bw, bh).data;
      const col = new Float32Array(bw), row = new Float32Array(bh);
      for (let y = 0; y < bh; y++) for (let x = 0; x < bw; x++) {
        const a = d[(y * bw + x) * 4 + 3] / 255;
        if (a > col[x]) col[x] = a;
        if (a > row[y]) row[y] = a;
      }
      let l = 0; while (l < bw && col[l] === 0) l++;
      let r = bw - 1; while (r >= 0 && col[r] === 0) r--;
      let t = 0; while (t < bh && row[t] === 0) t++;
      let b = bh - 1; while (b >= 0 && row[b] === 0) b--;
      if (l > r) { rows[cp] = null; continue; }
      rows[cp] = [r2(x0 + l + 1 - col[l] - X0), r2(x0 + r + col[r] - X0),
                  r2(BASE - (y0 + t + 1 - row[t])), r2(BASE - (y0 + b + row[b]))];
    }
    out[`${fam}|${w}`] = rows;
  }
  return out;
})()
