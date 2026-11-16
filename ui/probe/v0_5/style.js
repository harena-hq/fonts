// Evaluated in the probe page. CONFIG = { family, url, rows: [{point, icons: [name...]}] }. For each
// row, how much of a 24 px square the Segoe glyph and each icon ink, each drawn at its own extent.
(async () => {
  const F = await (await fetch(CONFIG.url)).json();
  await document.fonts.load(`100px "${CONFIG.family}"`);
  const [N, M] = [256, 24];
  const big = document.createElement('canvas');
  big.width = big.height = N;
  const b = big.getContext('2d', { willReadFrequently: true });
  const small = document.createElement('canvas');
  small.width = small.height = M;
  const s = small.getContext('2d', { willReadFrequently: true });
  const vector = () => {
    const d = b.getImageData(0, 0, N, N).data;
    let [x0, x1, y0, y1] = [N, -1, N, -1];
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) if (d[(y * N + x) * 4 + 3] > 64) {
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
    if (x1 < 0) return null;
    const [w, h] = [x1 - x0 + 1, y1 - y0 + 1];
    const k = (M - 2) / Math.max(w, h);
    s.clearRect(0, 0, M, M);
    s.imageSmoothingQuality = 'high';
    s.drawImage(big, x0, y0, w, h, (M - w * k) / 2, (M - h * k) / 2, w * k, h * k);
    const e = s.getImageData(0, 0, M, M).data;
    let ink = 0;
    for (let i = 0; i < M * M; i++) ink += e[i * 4 + 3] / 255;
    return +(ink / (M * M)).toFixed(4);
  };
  const out = {};
  for (const r of CONFIG.rows) {
    b.setTransform(1, 0, 0, 1, 0, 0);
    b.clearRect(0, 0, N, N);
    const ch = String.fromCodePoint(parseInt(r.point, 16));
    b.font = `120px "${CONFIG.family}"`;
    const a = b.measureText(ch).width;
    b.font = `${a > 120.5 ? 120 * 120 / a : 120}px "${CONFIG.family}"`;
    b.fillText(ch, 8, 170);
    const scores = { segoe: vector() };
    for (const name of r.icons) {
      const f = F[name];
      b.setTransform(1, 0, 0, 1, 0, 0);
      b.clearRect(0, 0, N, N);
      const k = (N - 16) / f.z;
      b.setTransform(k, 0, 0, k, 8, 8);
      b.fill(new Path2D(f.d), f.e ? 'evenodd' : 'nonzero');
      b.setTransform(1, 0, 0, 1, 0, 0);
      scores[name] = vector();
    }
    out[r.point] = scores;
  }
  return out;
})()
