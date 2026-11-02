// Evaluated in the probe page. CONFIG = { font, url, rows: [{point, icon}] }. How closely this font's
// glyph draws the SVG it came from: the cosine of the two, inked to 64 px at their own extents.
(async () => {
  const F = await (await fetch(CONFIG.url)).json();
  const face = new FontFace('Built', `url(${CONFIG.font})`);
  document.fonts.add(await face.load());
  const [N, M] = [700, 64];
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
    const v = new Float32Array(M * M);
    let n = 0;
    for (let i = 0; i < M * M; i++) { v[i] = e[i * 4 + 3] / 255; n += v[i] * v[i]; }
    n = Math.sqrt(n);
    for (let i = 0; i < M * M; i++) v[i] /= n;
    return v;
  };
  const out = {};
  for (const r of CONFIG.rows) {
    b.setTransform(1, 0, 0, 1, 0, 0);
    b.clearRect(0, 0, N, N);
    b.font = '420px "Built"';
    b.fillText(String.fromCodePoint(parseInt(r.point, 16)), 40, 460);
    const v = vector();
    const f = F[r.icon];
    b.clearRect(0, 0, N, N);
    const k = 420 / f.z;
    b.setTransform(k, 0, 0, k, 40, 40);
    b.fill(new Path2D(f.d), f.e ? 'evenodd' : 'nonzero');
    const w = vector();
    let t = 0;
    for (let i = 0; i < M * M; i++) t += v[i] * w[i];
    out[r.point] = +t.toFixed(4);
  }
  return out;
})()
