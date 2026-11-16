// Evaluated in the probe page. CONFIG = { families: [[name, weight], ...], chars: "lI", row }.
// Stem width = summed pixel coverage along one row `row` px above the baseline
// (default 250), rendered at 1000 px. The row must cross only the vertical stem:
// 250 does for `l` and `I` in every font measured; 650 does for `ㅣ` (U+3163)
// and `十`, above the latter's crossbar. A vertical stem is a rectangle, so the sum is its width with
// sub-pixel precision regardless of anti-aliasing.
(async () => {
  for (const [fam, w] of CONFIG.families) await document.fonts.load(`${w} 100px "${fam}"`);
  const PX = 1000, W = 1400, H = 1400, BASE = 1100, ROW = BASE - (CONFIG.row ?? 250);
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d', { willReadFrequently: true });
  const out = {};
  for (const [fam, w] of CONFIG.families) {
    const r = {};
    for (const ch of CONFIG.chars) {
      g.clearRect(0, 0, W, H);
      g.font = `${w} ${PX}px "${fam}"`; g.fillStyle = '#000'; g.fillText(ch, 200, BASE);
      const d = g.getImageData(0, ROW, W, 1).data;
      let s = 0; for (let i = 3; i < d.length; i += 4) s += d[i] / 255;
      r[ch] = Math.round(s * 100) / 100;
    }
    out[`${fam}|${w}`] = r;
  }
  return out;
})()
