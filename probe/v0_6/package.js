// Evaluated in the probe page. CONFIG = { sheets: [url], mode, ... }. Links the package's stylesheets,
// then, by mode:
//  widths: { faces: [{ family, weight, ttf }], strings, langs, px } - each string's DOM width in the
//          package's family against the same face loaded whole from its TTF; returns the differences.
//  lines:  { faces: [{ family, stack, weight }], points, langs, sizes } - the line box of "A" and one
//          code point under the Segoe stack, and with the package's family after it; returns, per
//          face, language and size, the code points whose line box differs.
//  fetch:  { texts: [{ key, stack, weight, lang, text }] } - the font files each text makes the page
//          fetch, from the resource list, one text per page load.
(async () => {
  for (const href of CONFIG.sheets) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    const done = new Promise((ok, fail) => { link.onload = ok; link.onerror = fail; });
    document.head.append(link);
    await done;
  }
  const span = document.createElement('span');
  span.style.cssText = 'position:absolute;white-space:pre;top:0;left:0';
  document.body.append(span);
  const loadFamily = (family) => Promise.all([...document.fonts].filter((f) => f.family === family || f.family === `"${family}"`).map((f) => f.load()));
  if (CONFIG.mode === 'widths') {
    const out = { measured: 0, differs: [] };
    for (const face of CONFIG.faces) {
      const ref = new FontFace(`Ref ${face.family} ${face.weight}`, `url(${face.ttf})`, { weight: String(face.weight) });
      document.fonts.add(await ref.load());
      await loadFamily(face.family);
      for (const lang of CONFIG.langs) {
        if (lang) span.lang = lang; else span.removeAttribute('lang');
        for (const text of CONFIG.strings) {
          span.textContent = text;
          span.style.font = `${face.weight} ${CONFIG.px}px "${face.family}"`;
          const ours = span.getBoundingClientRect().width;
          span.style.font = `${face.weight} ${CONFIG.px}px "Ref ${face.family} ${face.weight}"`;
          const whole = span.getBoundingClientRect().width;
          out.measured++;
          if (ours !== whole) out.differs.push([face.family, face.weight, lang, text, ours, whole]);
        }
      }
    }
    return out;
  }
  if (CONFIG.mode === 'lines') {
    const out = { measured: 0, differs: {} };
    const div = document.createElement('div');
    div.style.cssText = 'position:absolute;white-space:pre;line-height:normal';
    document.body.append(div);
    for (const face of CONFIG.faces) {
      await loadFamily(face.family);
      for (const lang of CONFIG.langs) {
        if (lang) div.lang = lang; else div.removeAttribute('lang');
        for (const px of CONFIG.sizes) {
          const key = `${face.family}|${face.weight}|${lang}|${px}`;
          const bad = out.differs[key] = [];
          for (const c of CONFIG.points) {
            div.textContent = 'A' + String.fromCodePoint(c);
            div.style.font = `${face.weight} ${px}px ${face.stack}`;
            const windows = div.getBoundingClientRect().height;
            div.style.font = `${face.weight} ${px}px ${face.stack}, "${face.family}"`;
            const ours = div.getBoundingClientRect().height;
            out.measured++;
            if (windows !== ours) bad.push(c);
          }
        }
      }
    }
    return out;
  }
  if (CONFIG.mode === 'fetch') {
    const t = CONFIG.text;
    const div = document.createElement('div');
    if (t.lang) div.lang = t.lang;
    div.style.font = `${t.weight} 20px ${t.stack}`;
    div.textContent = t.text;
    document.body.append(div);
    await document.fonts.ready;
    await new Promise((ok) => setTimeout(ok, 300));
    await document.fonts.ready;
    return performance.getEntriesByType('resource').map((e) => e.name).filter((n) => n.includes('.woff2')).map((n) => n.split('/').pop());
  }
})()
