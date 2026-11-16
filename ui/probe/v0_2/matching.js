// Evaluated in the probe page. CONFIG = { sizes: [family, ...], weights: [named weight, ...],
// text }. Which named face Edge draws for each CSS weight 1-1000, and what it draws for italic.
// A face is told apart by the width of `text`, which differs between named weights; the scan is
// made in canvas at 1000 px and in DOM layout at 100 px, scaled to 1000. Each size's answer is
// a list of runs [first weight, named weight] per layout; a width matching no named weight is
// reported as null. `variation`: DOM widths at weight 400 under font-variation-settings 'wght'
// n, which are Regular's if the setting is ignored. Italic: per named weight, the italic width
// in canvas and in DOM, and the slant of `l`'s left ink edge, dx/dy between 100 and 600 px
// above the baseline, negative for a forward (rightward) lean, as OpenType's italicAngle.
(async () => {
  const PX = 1000;
  const cv = document.createElement('canvas').getContext('2d');
  const width = (style, w, fam) => { cv.font = `${style} ${w} ${PX}px "${fam}"`; return cv.measureText(CONFIG.text).width; };
  const span = document.createElement('span');
  document.body.append(span);
  const dom = (style, w, fam, fvs = 'normal') => {
    span.style.cssText = `position:absolute;white-space:pre;font:${style} ${w} 100px "${fam}";` +
      `font-variation-settings:${fvs}`;
    span.textContent = CONFIG.text;
    return span.getBoundingClientRect().width * 10;
  };
  const leftEdge = (style, w, fam, rows) => {
    const c = document.createElement('canvas'); c.width = 1200; c.height = 1400;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.font = `${style} ${w} ${PX}px "${fam}"`; g.fillText('l', 400, 1200);
    return rows.map((h) => {
      const d = g.getImageData(0, 1200 - h, 1200, 1).data;
      for (let x = 0; x < 1200; x++) if (d[x * 4 + 3] >= 128) return x;
      return null;
    });
  };
  const r2 = (x) => Math.round(x * 100) / 100;
  const out = {};
  for (const fam of CONFIG.sizes) {
    for (const w of CONFIG.weights) for (const st of ['normal', 'italic']) await document.fonts.load(`${st} ${w} 100px "${fam}"`);
    const scan = (measure) => {
      const named = Object.fromEntries(CONFIG.weights.map((w) => [w, measure('normal', w, fam)]));
      if (new Set(Object.values(named)).size !== CONFIG.weights.length) throw new Error(`${fam}: named widths coincide`);
      const runs = [];
      let prev;
      for (let w = 1; w <= 1000; w++) {
        const x = measure('normal', w, fam);
        const hit = CONFIG.weights.find((n) => named[n] === x) ?? null;
        if (hit !== prev) { runs.push([w, hit]); prev = hit; }
      }
      return [named, runs];
    };
    const [named, runs] = scan(width);
    const [domNamed, domRuns] = scan(dom);
    const variation = Object.fromEntries([300, 350, 500, 600, 700].map(
      (n) => [n, r2(dom('normal', 400, fam, `'wght' ${n}`))]));
    variation.regular = r2(domNamed[400]);
    const italic = {};
    for (const w of CONFIG.weights) {
      const up = leftEdge('normal', w, fam, [100, 600]), it = leftEdge('italic', w, fam, [100, 600]);
      italic[w] = { canvas: [r2(named[w]), r2(width('italic', w, fam))],
                    dom: [r2(dom('normal', w, fam)), r2(dom('italic', w, fam))],
                    slant: r2(((it[0] - it[1]) - (up[0] - up[1])) / 500) };
    }
    out[fam] = { weights: runs, dom_weights: domRuns, variation, italic };
  }
  return out;
})()
