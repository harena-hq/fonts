// Evaluated in the probe page. CONFIG = { cases: [{ key, font, weight, overrides, lang, text }],
// sizes: [...] }. Loads each font with the overrides (CSS percentages) and returns, per case,
// [px, Segoe stack's height, height with the font after the stack] wherever the two differ.
(async () => {
  const out = {};
  for (const c of CONFIG.cases) {
    const family = `Probe ${c.key.replace(/\W/g, '')}`;
    const pct = (v) => `${v}%`;
    const face = new FontFace(family, `url(${c.font})`, {
      weight: String(c.weight), ascentOverride: pct(c.overrides['ascent-override']),
      descentOverride: pct(c.overrides['descent-override']), lineGapOverride: pct(c.overrides['line-gap-override']),
    });
    document.fonts.add(await face.load());
    const div = document.createElement('div');
    document.body.append(div);
    if (c.lang) div.lang = c.lang;
    div.textContent = c.text;
    const rows = out[c.key] = [];
    for (const px of CONFIG.sizes) {
      div.style.cssText = `position:absolute;white-space:pre;line-height:normal;font-weight:${c.weight};font-size:${px}px;`;
      div.style.fontFamily = CONFIG.stack;
      const windows = div.getBoundingClientRect().height;
      div.style.fontFamily = `${CONFIG.stack}, "${family}"`;
      const ours = div.getBoundingClientRect().height;
      if (windows !== ours) rows.push([px, windows, ours]);
    }
    div.remove();
  }
  return out;
})()
