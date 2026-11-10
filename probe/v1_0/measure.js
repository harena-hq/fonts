// Evaluated in the probe page, in any engine. CONFIG = { sheets: [url], faces: [{ family, url, weight }],
// mode, ... }. Links the package's stylesheets, adds the faces (a whole TTF under its own family), then:
//  env:   the engine as the page sees it: user agent, device pixel ratio, languages.
//  boxes: { groups: [{ font, lang, texts, axis }] } - per group, each text's width (axis "width", a span
//         in its own line) or line box height (axis "height", a block at line-height: normal).
//  fetch: { font, lang, text } - the font files the page fetches to draw the text, by file name.
// Every read waits until laying the text out loads no further file: an engine may pick a file by
// unicode-range that lacks the character, and fetch another only when it lays the text out. A face
// that fails to load is an error, not a measurement. Returns numbers and names only.
(async () => {
  // A frame, or a timer where a hidden page draws none; layout is forced by reading geometry, not by it.
  const frame = () => new Promise((ok) => { requestAnimationFrame(() => ok()); setTimeout(ok, 50); });
  const failed = () => [...document.fonts].filter((f) => f.status === 'error').map((f) => f.family);
  const within = (promise, ms) => Promise.race([promise, new Promise((_, fail) => setTimeout(
    () => fail(new Error(`fonts still loading after ${ms} ms; page ${document.visibilityState}`)), ms))]);
  // Lay out, then wait for whatever that layout made the engine load, until a layout loads nothing.
  const settle = async (node) => {
    for (let round = 0; round < 50; round++) {
      node.getBoundingClientRect();
      await frame();
      await within(document.fonts.ready, 600000);
      if (document.fonts.status === 'loaded') {
        node.getBoundingClientRect();
        await frame();
        if (document.fonts.status === 'loaded') {
          const bad = failed();
          if (bad.length) throw new Error(`fonts failed: ${[...new Set(bad)].join(', ')}`);
          return;
        }
      }
    }
    throw new Error('fonts never settled');
  };
  for (const href of CONFIG.sheets || []) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    const done = new Promise((ok, fail) => { link.onload = ok; link.onerror = () => fail(new Error(`stylesheet ${href}`)); });
    document.head.append(link);
    await done;
  }
  for (const f of CONFIG.faces || []) {
    document.fonts.add(await new FontFace(f.family, `url(${f.url})`, { weight: String(f.weight) }).load());
  }
  if (CONFIG.mode === 'env') {
    return { userAgent: navigator.userAgent, devicePixelRatio, languages: [...navigator.languages] };
  }
  if (CONFIG.mode === 'fetch') {
    const div = document.createElement('div');
    if (CONFIG.lang) div.lang = CONFIG.lang;
    div.style.font = CONFIG.font;
    div.textContent = CONFIG.text;
    document.body.append(div);
    await settle(div);
    return performance.getEntriesByType('resource').map((e) => e.name)
      .filter((n) => n.endsWith('.woff2')).map((n) => n.split('/').pop());
  }
  const out = [];
  for (const group of CONFIG.groups) {
    await document.fonts.load(group.font, group.texts.join(''));
    const box = document.createElement('div');
    box.style.cssText = 'position:absolute;top:0;left:0;white-space:pre;line-height:normal';
    box.style.font = group.font;
    if (group.lang) box.lang = group.lang;
    const nodes = group.texts.map((text) => {
      const line = document.createElement('div');
      if (group.axis === 'height') {
        line.textContent = text;
        box.append(line);
        return line;
      }
      const span = document.createElement('span');
      span.textContent = text;
      line.append(span);
      box.append(line);
      return span;
    });
    document.body.append(box);
    await settle(box);
    out.push(nodes.map((n) => (group.axis === 'height' ? n.getBoundingClientRect().height : n.getBoundingClientRect().width)));
    box.remove();
  }
  return out;
})()
