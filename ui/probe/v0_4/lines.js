// Evaluated in the probe page. CONFIG = { family, weight, css, texts: {name: text},
// langs: [...], sizes: [...] }. The height of a block holding one line of text, at
// `line-height: normal`, per language, text and px size: { lang: { name: { px: h } } }.
// `font` (optional) is loaded under `family`.
(async () => {
  if (CONFIG.font) {
    const face = new FontFace(CONFIG.family, `url(${CONFIG.font})`, { weight: String(CONFIG.weight) });
    document.fonts.add(await face.load());
  }
  const div = document.createElement('div');
  document.body.append(div);
  const out = {};
  for (const lang of CONFIG.langs) {
    if (lang) div.lang = lang; else div.removeAttribute('lang');
    const rows = out[lang] = {};
    for (const [name, text] of Object.entries(CONFIG.texts)) {
      const row = rows[name] = {};
      for (const px of CONFIG.sizes) {
        div.style.cssText = `position:absolute;white-space:pre;line-height:normal;` +
          `font-family:"${CONFIG.family}";font-weight:${CONFIG.weight};font-size:${px}px;`;
        div.textContent = text;
        row[px] = div.getBoundingClientRect().height;
      }
    }
  }
  return out;
})()
