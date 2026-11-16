// Evaluated in the probe page. CONFIG = { family, weight, font?, cases: [{text, css, lang}],
// bases: [...], marks: [...], langs: [...] }. DOM span widths at 1000 px, as page layout sees
// them. `cases` come back as one width each, in order. For marks, each base followed by each
// mark, per language: the width minus the base's own, kept only where it is not zero.
// `font` (optional) is loaded under `family`.
(async () => {
  if (CONFIG.font) {
    const face = new FontFace(CONFIG.family, `url(${CONFIG.font})`);
    document.fonts.add(await face.load());
  }
  const span = document.createElement('span');
  document.body.append(span);
  const base = `position:absolute;white-space:pre;font-family:"${CONFIG.family}";` +
    `font-weight:${CONFIG.weight};font-size:1000px;`;
  const width = (text, css, lang) => {
    if (lang) span.lang = lang; else span.removeAttribute('lang');
    span.style.cssText = base + (css || '');
    span.textContent = text;
    return span.getBoundingClientRect().width;
  };
  const cases = CONFIG.cases.map((c) => width(c.text, c.css, c.lang));
  const marks = {};
  for (const lang of CONFIG.langs || []) {
    const out = marks[lang] = {};
    for (const b of CONFIG.bases) {
      const bw = width(b, '', lang);
      for (const m of CONFIG.marks) {
        const d = width(b + m, '', lang) - bw;
        if (d !== 0) out[b + m] = d;
      }
    }
  }
  return { cases, marks };
})()
