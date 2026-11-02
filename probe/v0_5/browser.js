// Evaluated in the probe page. CONFIG = { font, points, sizes, styles, stack }. Every code point under
// Segoe Fluent Icons and under Harena UI Icons at each size and style, in DOM and canvas; line boxes;
// and that a stack naming Segoe first draws Segoe's pixels. Returns only what differs, and counts.
(async () => {
  const face = new FontFace('Harena UI Icons', `url(${CONFIG.font})`);
  document.fonts.add(await face.load());
  await document.fonts.load('20px "Segoe Fluent Icons"');
  const span = document.createElement('span');
  document.body.append(span);
  const ctx = document.createElement('canvas').getContext('2d');
  const widths = (family, size, style, ch) => {
    span.style.cssText = `position:absolute;white-space:pre;font-family:"${family}";font-size:${size}px;${style.css}`;
    span.textContent = ch;
    ctx.font = `${style.canvas} ${size}px "${family}"`;
    return [span.getBoundingClientRect().width, ctx.measureText(ch).width];
  };
  const off = [];
  let measured = 0;
  for (const size of CONFIG.sizes) {
    const unit = 1 / 64 + 1e-6;
    for (const style of CONFIG.styles) {
      for (const p of CONFIG.points) {
        const ch = String.fromCodePoint(parseInt(p, 16));
        const [a, b] = [widths('Segoe Fluent Icons', size, style, ch), widths('Harena UI Icons', size, style, ch)];
        measured += 2;
        if (Math.abs(a[0] - b[0]) > unit || Math.abs(a[1] - b[1]) > unit) off.push([p, size, style.css, a, b]);
      }
    }
  }
  const heights = {};
  const block = document.createElement('div');
  document.body.append(block);
  for (const size of CONFIG.sizes) {
    heights[size] = ['Segoe Fluent Icons', 'Harena UI Icons'].map((family) => {
      block.style.cssText = `position:absolute;font-family:"${family}";font-size:${size}px;line-height:normal`;
      block.textContent = '';
      return block.getBoundingClientRect().height;
    });
  }
  const text = new FontFace('Harena UI Text', `url(${CONFIG.text})`);
  document.fonts.add(await text.load());
  await document.fonts.load('16px "Segoe UI Variable Text"');
  const line = document.createElement('div');
  document.body.append(line);
  const strings = [];
  for (const size of [12, 14, 16, 20]) for (const s of CONFIG.strings) {
    strings.push([s, size, ...['"Segoe UI Variable Text", "Segoe Fluent Icons"', '"Harena UI Text", "Harena UI Icons"'].map((stack) => {
      line.style.cssText = `position:absolute;white-space:pre;line-height:normal;font-family:${stack};font-size:${size}px`;
      line.textContent = s;
      const r = line.getBoundingClientRect();
      return [r.width, r.height];
    })]);
  }
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 48;
  const pix = canvas.getContext('2d', { willReadFrequently: true });
  const draw = (stack, ch) => {
    pix.clearRect(0, 0, 48, 48);
    pix.font = `32px ${stack}`;
    pix.fillText(ch, 4, 40);
    return pix.getImageData(0, 0, 48, 48).data;
  };
  let stackDiffers = 0;
  const differs = [];
  for (const p of CONFIG.points) {
    const ch = String.fromCodePoint(parseInt(p, 16));
    const [x, y] = [draw('"Segoe Fluent Icons"', ch), draw('"Segoe Fluent Icons", "Harena UI Icons"', ch)];
    let same = true;
    for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) { same = false; break; }
    if (!same) { stackDiffers++; differs.push(p); }
  }
  return { measured, off: off.slice(0, 40), offCount: off.length, heights, strings, stackDiffers, differs: differs.slice(0, 20) };
})()
