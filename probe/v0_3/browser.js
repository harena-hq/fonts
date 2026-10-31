// Evaluated in the probe page. CONFIG = { font, family, weight, small, sizes: [...],
// cases: [{text, css, lang}], marks: [text, ...], langs: [...], info: [text, ...] }. Item 4:
// one built face, served as a web font declared at exactly its weight, against the Segoe
// face `family` at `weight`, in DOM layout at each size: every feature case under its CSS
// and language, and every base+mark text under each language. Compared here, so only what is
// outside the tolerance comes back: 0.1% of Segoe's width, or for a Small face within one
// layout unit (1/64 px), as v0.2's check. `info` texts are measured the same way and returned
// whole, outside the tolerance or not; they are reported, not judged. Returns {font (the
// bytes loaded, base64), count, unit, over: [[what, ours, theirs]], info: [[what, ours,
// theirs]], segoe: [Segoe's width of each case at 1000 px, if measured]}, widths in px per
// 1000 px of size.
(async () => {
  const w = CONFIG.weight;
  const bytes = await (await fetch(CONFIG.font)).arrayBuffer();
  // the page is not a secure context, so no crypto.subtle: the bytes go back, base64, and
  // are hashed by the caller
  const u8 = new Uint8Array(bytes);
  let bin = '';
  for (let i = 0; i < u8.length; i += 0x8000) bin += String.fromCharCode(...u8.subarray(i, i + 0x8000));
  const face = new FontFace('Harena UI Check', bytes, { weight: String(w) });
  document.fonts.add(await face.load());
  await document.fonts.load(`${w} 100px "${CONFIG.family}"`);
  const span = document.createElement('span');
  document.body.append(span);
  const dom = (fam, px, text, css, lang) => {
    if (lang) span.lang = lang; else span.removeAttribute('lang');
    span.style.cssText = `position:absolute;white-space:pre;font-family:"${fam}";font-weight:${w};` +
      `font-size:${px}px;${css || ''}`;
    span.textContent = text;
    return span.getBoundingClientRect().width * 1000 / px;
  };
  const out = { font: btoa(bin), count: 0, unit: 0, over: [], info: [], segoe: [] };
  const compare = (px, text, css, lang) => {
    const ours = dom('Harena UI Check', px, text, css, lang);
    const theirs = dom(CONFIG.family, px, text, css, lang);
    out.count++;
    if (Math.abs(ours - theirs) <= 0.001 * theirs) return theirs;
    if (CONFIG.small && Math.abs(ours - theirs) * px / 1000 <= 1 / 64 + 1e-9) { out.unit++; return theirs; }
    out.over.push([`${px} px ${css || ''} lang=${lang || '-'} ${JSON.stringify(text)}`, ours, theirs]);
    return theirs;
  };
  for (const px of CONFIG.sizes) {
    for (const c of CONFIG.cases) {
      const theirs = compare(px, c.text, c.css, c.lang);
      if (px === 1000) out.segoe.push(theirs);
    }
    for (const lang of CONFIG.langs) for (const t of CONFIG.marks) compare(px, t, '', lang);
    for (const lang of CONFIG.langs) for (const t of CONFIG.info || [])
      out.info.push([`${px} px lang=${lang || '-'} ${JSON.stringify(t)}`,
                     dom('Harena UI Check', px, t, '', lang), dom(CONFIG.family, px, t, '', lang)]);
  }
  return out;
})()
