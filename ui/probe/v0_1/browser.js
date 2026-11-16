// Evaluated in the probe page. CONFIG = { font: url, strings: [...], weight }.
// Done-when 9: each string's width in the built font, served as a web font,
// against Segoe UI Variable Text in the same browser. Canvas, 1000 px, kerning on.
(async () => {
  const face = new FontFace('Harena UI Check', `url(${CONFIG.font})`, { weight: String(CONFIG.weight) });
  document.fonts.add(await face.load());
  const cv = document.createElement('canvas').getContext('2d');
  cv.fontKerning = 'normal';
  const out = {};
  for (const s of CONFIG.strings) {
    cv.font = `${CONFIG.weight} 1000px "Harena UI Check"`;
    const ours = cv.measureText(s).width;
    cv.font = `${CONFIG.weight} 1000px "Segoe UI Variable Text"`;
    out[s] = [ours, cv.measureText(s).width];
  }
  return out;
})()
