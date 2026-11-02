// Evaluated in the probe page. CONFIG = { family, points: [hex...], sizes: [...] }. For each
// point: DOM width at 2048 px (one font unit per px) and ink [left, right, bottom, top] as pixel
// edges at 256 px, in font units. measureText's boxes are coarser than the outline at any size.
// `heights`: the height of a line of the font per size.
(async () => {
  await document.fonts.load(`20px "${CONFIG.family}"`);
  const span = document.createElement('span');
  document.body.append(span);
  span.style.cssText = `position:absolute;white-space:pre;font-family:"${CONFIG.family}";font-size:2048px;`;
  const canvas = document.createElement('canvas');
  const [W, H, ORIGIN, BASE] = [900, 340, 40, 300];
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.font = `256px "${CONFIG.family}"`;
  const ink = (ch) => {
    ctx.clearRect(0, 0, W, H);
    ctx.fillText(ch, ORIGIN, BASE);
    const d = ctx.getImageData(0, 0, W, H).data;
    let [x0, x1, y0, y1] = [W, -1, H, -1];
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (d[(y * W + x) * 4 + 3] > 127) {
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
    return x1 < 0 ? null : [x0 - ORIGIN, x1 + 1 - ORIGIN, BASE - y1 - 1, BASE - y0].map((v) => v * 8);
  };
  const out = {};
  for (const p of CONFIG.points) {
    const ch = String.fromCodePoint(parseInt(p, 16));
    span.textContent = ch;
    out[p] = [span.getBoundingClientRect().width, ink(ch)];
  }
  const block = document.createElement('div');
  document.body.append(block);
  const heights = {};
  for (const s of CONFIG.sizes) {
    block.style.cssText = `position:absolute;font-family:"${CONFIG.family}";font-size:${s}px;`;
    block.textContent = '\uE700';
    heights[s] = block.getBoundingClientRect().height;
  }
  return { out, heights };
})()
