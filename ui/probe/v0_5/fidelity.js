// Evaluated in the probe page. CONFIG = { font, faces, symbols, url, rows }. How closely this font's glyph
// draws what its row asks for, drawn here from the sources: the cosine of the two, inked to 64 px at their
// own extents. Placement is not compared: the gate checks each glyph against Segoe's box.
const SYMBOL = { light: 300, regular: 400, bold: 700 };
(async () => {
  const F = await (await fetch(CONFIG.url)).json();
  const face = new FontFace('Built', `url(${CONFIG.font})`);
  document.fonts.add(await face.load());
  for (const [weight, url] of Object.entries(CONFIG.faces)) {
    document.fonts.add(await new FontFace(`Ref-${weight}`, `url(${url})`, { weight: '1 999' }).load());
  }
  document.fonts.add(await new FontFace('Ref-symbols', `url(${CONFIG.symbols})`, { weight: '100 900' }).load());
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
  const svg = (f, z = f.z, side = 420, x = 40, y = 40) => {
    b.save();
    b.transform(side / z, 0, 0, side / z, x, y);
    b.fill(new Path2D(f.d), f.e ? 'evenodd' : 'nonzero');
    b.restore();
  };
  // The recipes as canvas operations, not the build's outline operations: on a 20 grid, a badge of 11 at
  // the bottom right, over a circle cleared 1 unit beyond it; the symbol a filled circle knocks out.
  const compose = (r) => {
    const u = 420 / 20;
    svg(F[r.icon]);
    b.save();
    b.globalCompositeOperation = 'destination-out';
    b.beginPath();
    b.arc(40 + 14.5 * u, 40 + 14.5 * u, 6.5 * u, 0, 2 * Math.PI);
    b.fill();
    b.restore();
    svg(F[r.badge], F[r.badge].z, 11 * u, 40 + 9 * u, 40 + 9 * u);
  };
  const holes = (r) => {
    svg(F[r.icon]);
    const d = b.getImageData(0, 0, N, N).data;
    let [x0, x1] = [N, -1];
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) if (d[(y * N + x) * 4 + 3] > 64) {
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
    }
    b.clearRect(0, 0, N, N);
    b.beginPath();
    b.arc((x0 + x1 + 1) / 2, 40 + 210, (x1 - x0 + 1) / 2 - 4, 0, 2 * Math.PI);  // short of the rim: no ring of edge pixels
    b.fill();
    b.save();
    b.globalCompositeOperation = 'destination-out';
    svg(F[r.icon]);
    b.restore();
  };
  // Text by the browser's own fallback: the face where it has the character, Pretendard JP where not.
  const text = (r, px) => {
    b.font = `${SYMBOL[r.weight]} ${px}px "Ref-${r.weight}", "Ref-symbols"`;
    b.fillText(r.text, 40, 460);
  };
  const width = (r) => {
    b.font = `${SYMBOL[r.weight]} 420px "Ref-${r.weight}", "Ref-symbols"`;
    return b.measureText(r.text).width;
  };
  // Bars drawn as rectangles, an empty one cleared inside: x, width, heights and line on the 20 grid.
  const bars = (r) => {
    const u = 420 / 20;
    [2, 6.5, 11, 15.5].forEach((x, i) => {
      const h = [5, 9, 13, 17][i];
      b.fillRect(40 + x * u, 40 + (18 - h) * u, 3 * u, h * u);
      if (i >= r.level) b.clearRect(40 + (x + 1) * u, 40 + (19 - h) * u, 1 * u, (h - 2) * u);
    });
  };
  const paint = (r) => {
    if (r.kind === 'mirror') {
      b.save();
      b.transform(-1, 0, 0, 1, N, 0);
      paint(r.of);
      b.restore();
    } else if (r.kind === 'compose') compose(r);
    else if (r.kind === 'holes') holes(r);
    else if (r.kind === 'bars') bars(r);
    else if (r.kind === 'text') text(r, 420 * Math.min(1, 620 / width(r)));
    else if (r.rotate) {  // a quarter turn counterclockwise, about the centre of the drawing's square
      b.save();
      b.transform(0, -1, 1, 0, 0, 500);
      svg(F[r.icon]);
      b.restore();
    } else svg(F[r.icon]);
  };
  const out = {};
  for (const r of CONFIG.rows) {
    b.setTransform(1, 0, 0, 1, 0, 0);
    b.clearRect(0, 0, N, N);
    b.font = '420px "Built"';
    const ch = String.fromCodePoint(parseInt(r.point, 16));
    const px = 420 * Math.min(1, 620 / b.measureText(ch).width);
    b.font = `${px}px "Built"`;
    b.fillText(ch, 40, 460);
    const v = vector();
    b.clearRect(0, 0, N, N);
    paint(r);
    const w = vector();
    let t = 0;
    if (v && w) for (let i = 0; i < M * M; i++) t += v[i] * w[i];
    out[r.point] = +t.toFixed(4);
  }
  return out;
})()
