// Evaluated in the probe page. CONFIG = { family, url, rows: [{n, point, label, cand: [stem...], filled}],
// perSheet }. One PNG per perSheet rows: the Segoe glyph beside up to eight Fluent icons, lettered.
// Sheets go to `.private/` only: they hold Segoe's pixels.
(async () => {
  const F = await (await fetch(CONFIG.url)).json();
  await document.fonts.load(`50px "${CONFIG.family}"`);
  const order = (filled) => (filled
    ? ['_20_filled', '_16_filled', '_24_filled', '_20_regular', '_16_regular', '_24_regular']
    : ['_20_regular', '_16_regular', '_24_regular', '_20_filled', '_16_filled', '_24_filled']);
  const pick = (s, filled) => { for (const q of order(filled)) if (F[s + q]) return F[s + q]; return null; };
  const [CELL, H, LEFT] = [74, 80, 130];
  const out = [];
  for (let g = 0; g < CONFIG.rows.length; g += CONFIG.perSheet) {
    const part = CONFIG.rows.slice(g, g + CONFIG.perSheet);
    const c = document.createElement('canvas');
    c.width = LEFT + 8 * CELL;
    c.height = part.length * H + 18;
    const x = c.getContext('2d');
    x.fillStyle = '#fff';
    x.fillRect(0, 0, c.width, c.height);
    x.fillStyle = '#333';
    x.font = '12px sans-serif';
    x.fillText('TARGET', 36, 13);
    'ABCDEFGH'.split('').forEach((l, i) => x.fillText(l, LEFT + i * CELL + 22, 13));
    part.forEach((r, i) => {
      const y = 18 + i * H;
      x.fillStyle = '#eef';
      x.fillRect(0, y, LEFT - 8, H - 3);
      x.fillStyle = '#000';
      x.font = `50px "${CONFIG.family}"`;
      const ch = String.fromCodePoint(parseInt(r.point, 16));
      const w = x.measureText(ch).width;
      if (w > 110) x.font = `${50 * 110 / w}px "${CONFIG.family}"`;
      x.fillText(ch, w > 60 ? 6 : 36, y + 54);
      x.font = '10px sans-serif';
      x.fillStyle = '#06c';
      x.fillText(`${r.n} ${(r.label || r.point).slice(0, 18)}`, 3, y + 70);
      r.cand.forEach((s, j) => {
        const f = pick(s, r.filled);
        if (!f) return;
        x.save();
        const k = 50 / f.z;
        x.translate(LEFT + j * CELL + 10, y + 6);
        x.scale(k, k);
        x.fillStyle = '#000';
        x.fill(new Path2D(f.d), f.e ? 'evenodd' : 'nonzero');
        x.restore();
        x.font = '10px sans-serif';
        x.fillStyle = '#888';
        x.fillText('ABCDEFGH'[j], LEFT + j * CELL, y + 12);
      });
    });
    out.push(c.toDataURL('image/png'));
  }
  return out;
})()
