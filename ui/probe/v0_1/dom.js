// Evaluated in the probe page. CONFIG = { font, families: [...], strings: [...], sizes: [...],
// numeric: "normal" | "tabular-nums", weight (default 400) }. DOM span widths, as page layout
// sees them, in px per 1000 px of font size. `font` (optional) is loaded as "Harena UI Check".
(async () => {
  if (CONFIG.font) {
    const face = new FontFace('Harena UI Check', `url(${CONFIG.font})`);
    document.fonts.add(await face.load());
  }
  const span = document.createElement('span');
  document.body.append(span);
  const out = {};
  for (const fam of CONFIG.families) for (const px of CONFIG.sizes) for (const s of CONFIG.strings) {
    span.style.cssText = `position:absolute;white-space:pre;font-family:"${fam}";` +
      `font-weight:${CONFIG.weight ?? 400};font-size:${px}px;font-variant-numeric:${CONFIG.numeric || 'normal'};`;
    span.textContent = s;
    out[`${fam}|${px}|${s}`] = span.getBoundingClientRect().width * 1000 / px;
  }
  return out;
})()
