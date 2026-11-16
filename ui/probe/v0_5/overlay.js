// Evaluated in the probe page. CONFIG = { font, rows: [{n, point, label}], perSheet }. Each row: Segoe's
// glyph, this font's, and both over each other in two colours, at 72 px and at 20 and 16 px.
// Sheets go to `.private/` only: they hold Segoe's pixels.
(async () => {
  const face = new FontFace('Harena UI Icons', `url(${CONFIG.font})`);
  document.fonts.add(await face.load());
  await document.fonts.load('72px "Segoe Fluent Icons"');
  const out = [];
  const [W, H, COLS] = [230, 96, 4];
  for (let g = 0; g < CONFIG.rows.length; g += CONFIG.perSheet) {
    const part = CONFIG.rows.slice(g, g + CONFIG.perSheet);
    const c = document.createElement('canvas');
    c.width = W * COLS;
    c.height = Math.ceil(part.length / COLS) * H;
    const x = c.getContext('2d');
    x.fillStyle = '#fff';
    x.fillRect(0, 0, c.width, c.height);
    part.forEach((r, i) => {
      const [X, Y] = [(i % COLS) * W, Math.floor(i / COLS) * H];
      const ch = String.fromCodePoint(parseInt(r.point, 16));
      const draw = (fam, size, px, py, color) => {
        x.font = `${size}px "${fam}"`;
        x.fillStyle = color;
        x.fillText(ch, px, py);
      };
      x.font = '72px "Segoe Fluent Icons"';
      const scale = Math.min(1, 72 / x.measureText(ch).width);
      const big = 72 * scale;
      draw('Segoe Fluent Icons', big, X + 2, Y + 74, '#000');
      draw('Harena UI Icons', big, X + 76, Y + 74, '#000');
      draw('Harena UI Icons', 20, X + 154, Y + 28, '#000');
      draw('Harena UI Icons', 16, X + 180, Y + 26, '#000');
      x.font = '10px sans-serif';
      x.fillStyle = '#06c';
      x.fillText(`${r.n} ${(r.label || r.point).slice(0, 34)}`, X + 2, Y + 90);
      x.strokeStyle = '#ddd';
      x.strokeRect(X, Y, W, H);
    });
    out.push(c.toDataURL('image/png'));
  }
  return out;
})()
