// Evaluated in the probe page. CONFIG = { font, family, weight, canvas: [...], dom: {numeric:
// [...]}, sizes: [...] }. Item 4: one built face, served as a web font declared at exactly its
// weight (no range, so this measures the face, not matching), against the Segoe face `family`
// at `weight` in the same browser. Canvas at 1000 px, kerning on; DOM span widths at each size,
// upright and italic (synthesized for both), per 1000 px of size. Returns [what, ours, theirs].
(async () => {
  const w = CONFIG.weight;
  const face = new FontFace('Harena UI Check', `url(${CONFIG.font})`, { weight: String(w) });
  document.fonts.add(await face.load());
  for (const st of ['normal', 'italic']) await document.fonts.load(`${st} ${w} 100px "${CONFIG.family}"`);
  const out = [];
  const cv = document.createElement('canvas').getContext('2d');
  cv.fontKerning = 'normal';
  for (const s of CONFIG.canvas) {
    cv.font = `${w} 1000px "Harena UI Check"`;
    const ours = cv.measureText(s).width;
    cv.font = `${w} 1000px "${CONFIG.family}"`;
    out.push([`canvas 1000 px ${JSON.stringify(s)}`, ours, cv.measureText(s).width]);
  }
  const span = document.createElement('span');
  document.body.append(span);
  const dom = (fam, st, numeric, px, s) => {
    span.style.cssText = `position:absolute;white-space:pre;font-family:"${fam}";font-weight:${w};` +
      `font-style:${st};font-size:${px}px;font-variant-numeric:${numeric};`;
    span.textContent = s;
    return span.getBoundingClientRect().width * 1000 / px;
  };
  for (const st of ['normal', 'italic']) for (const [numeric, strings] of Object.entries(CONFIG.dom))
    for (const px of CONFIG.sizes) for (const s of strings)
      out.push([`DOM ${px} px ${st} ${numeric} ${JSON.stringify(s)}`,
                dom('Harena UI Check', st, numeric, px, s), dom(CONFIG.family, st, numeric, px, s)]);
  return out;
})()
