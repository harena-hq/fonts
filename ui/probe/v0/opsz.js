// Evaluated in the probe page. CONFIG = { families: [...], weights: [...], text }.
// Does anything but the family name choose a Segoe UI Variable instance's opsz?
// The same text is measured per 1000 px of font size, by canvas and by a DOM span,
// across font sizes, font-optical-sizing and explicit opsz variation settings.
// One spread per family and weight is what matters; "Segoe UI" (the static
// family) and a missing family are included as comparisons.
(async () => {
  const cv = document.createElement('canvas').getContext('2d');
  const span = document.createElement('span');
  document.body.append(span);
  const dom = (fam, w, px, extra) => {
    span.style.cssText = `position:absolute;white-space:pre;font-family:"${fam}";font-weight:${w};font-size:${px}px;`;
    Object.assign(span.style, extra);
    span.textContent = CONFIG.text;
    return span.getBoundingClientRect().width * 1000 / px;
  };
  const out = {};
  for (const w of CONFIG.weights) for (const fam of CONFIG.families) {
    const r = {};
    for (const px of [8, 10.5, 14, 36, 100, 1000]) {
      cv.font = `${w} ${px}px "${fam}"`;
      r[`canvas@${px}`] = cv.measureText(CONFIG.text).width * 1000 / px;
      r[`dom@${px}`] = dom(fam, w, px, {});
      r[`dom@${px} optical-sizing none`] = dom(fam, w, px, { fontOpticalSizing: 'none' });
    }
    for (const o of [8, 10.5, 36]) r[`dom@1000 opsz ${o}`] = dom(fam, w, 1000, { fontVariationSettings: `"opsz" ${o}` });
    out[`${fam}|${w}`] = r;
  }
  return out;
})()
