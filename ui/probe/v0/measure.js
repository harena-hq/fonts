// Evaluated in the probe page. CONFIG is prepended by run.py:
//   { families: [[name, weight], ...], glyphs: [cp, ...], pairs: [cp, ...], strings: {...} }
(async () => {
  for (const [fam, w] of CONFIG.families) await document.fonts.load(`${w} 100px "${fam}"`);
  const PX = 1000;
  const cv = document.createElement('canvas').getContext('2d');
  cv.fontKerning = 'normal';
  const r2 = (x) => Math.round(x * 100) / 100;
  const out = {};
  for (const [fam, w] of CONFIG.families) {
    cv.font = `${w} ${PX}px "${fam}"`;
    const adv = {};
    const glyphs = {};
    for (const cp of CONFIG.glyphs) {
      const m = cv.measureText(String.fromCodePoint(cp));
      adv[cp] = m.width;
      glyphs[cp] = [r2(m.width), r2(-m.actualBoundingBoxLeft), r2(m.actualBoundingBoxRight),
                    r2(m.actualBoundingBoxAscent), r2(-m.actualBoundingBoxDescent)];
    }
    const kern = {};
    for (const a of CONFIG.pairs) for (const b of CONFIG.pairs) {
      const k = cv.measureText(String.fromCodePoint(a, b)).width - adv[a] - adv[b];
      if (Math.abs(k) >= 0.05) kern[`${a},${b}`] = r2(k);
    }
    const strings = {};
    for (const group of Object.values(CONFIG.strings)) for (const s of group) {
      cv.fontKerning = 'normal'; const kerned = cv.measureText(s).width;
      cv.fontKerning = 'none'; const plain = cv.measureText(s).width;
      cv.fontKerning = 'normal';
      strings[s] = [r2(kerned), r2(plain)];
    }
    out[`${fam}|${w}`] = { glyphs, kern, strings };
  }
  return out;
})()
