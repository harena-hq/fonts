// Evaluated in the probe page. CONFIG = { sheets: [url], groups: [{ font, lang, texts }] }. Links the
// package's stylesheets, loads what each group's font needs for its texts, and returns each text's
// width, per group in order: every text in its own block, laid out once per group.
(async () => {
  for (const href of CONFIG.sheets) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    const done = new Promise((ok, fail) => { link.onload = ok; link.onerror = fail; });
    document.head.append(link);
    await done;
  }
  const out = [];
  for (const group of CONFIG.groups) {
    await document.fonts.load(group.font, group.texts.join(''));
    const box = document.createElement('div');
    box.style.cssText = `position:absolute;top:0;left:0;white-space:pre;font:${group.font}`;
    if (group.lang) box.lang = group.lang;
    const spans = group.texts.map((text) => {
      const div = document.createElement('div');
      const span = document.createElement('span');
      span.textContent = text;
      div.append(span);
      box.append(div);
      return span;
    });
    document.body.append(box);
    out.push(spans.map((span) => span.getBoundingClientRect().width));
    box.remove();
  }
  return out;
})()
