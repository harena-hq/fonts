# SPDX-License-Identifier: Apache-2.0
"""Write build/specimen.html: Korean and Japanese UI labels set three ways, to be
rendered side by side in the reference browser.

1. Windows: "Segoe UI Variable Text" and whatever the browser falls back to.
2. Open Sans + Pretendard JP, adjusted as v0 proposes.
3. Open Sans + Noto Sans KR/JP, adjusted the same way.

"Adjusted" is approximated in CSS: CJK runs are scaled with `size-adjust`,
weighted through `font-variation-settings` to match the Windows face's stems,
and spaced with `letter-spacing` to a 1 em advance. Latin is Open Sans at
`wdth` 95 and the stem-matched weight. No font is built.

Usage: python probe/v0/specimen.py   (reads data/v0/cjk-windows.json and data/v0/stems.json)
"""
import json
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[2]
CJK = json.loads((ROOT / "data/v0/cjk-windows.json").read_text())["stems"]
LAT = json.loads((ROOT / "data/v0/stems.json").read_text())["matched_wght"]["Open Sans Probe"]
STRINGS = json.loads((ROOT / "probe/v0/cjk-strings.json").read_text())

# Windows targets: Hangul from Malgun Gothic's ㅣ, Japanese from Yu Gothic's 十.
TARGET = {("ko", 400): CJK["Malgun Gothic|400"]["ㅣ"], ("ko", 700): CJK["Malgun Gothic|700"]["ㅣ"],
          ("ja", 400): CJK["Yu Gothic|400"]["十"], ("ja", 700): CJK["Yu Gothic|700"]["十"]}
# candidate: script -> (probe family, stem glyph, scale, advance in em before scaling)
CANDS = {
    "pretendard": {"ko": ("Pretendard JP Probe", "ㅣ", 1.084, 0.864),
                   "ja": ("Pretendard JP Probe", "十", 1.0, 0.938)},
    "noto": {"ko": ("Noto Sans KR Probe", "ㅣ", 1.051, 0.920),
             "ja": ("Noto Sans JP Probe", "十", 0.95, 1.0)},
}


def wght_for(fam, ch, stem):
    scan = sorted((int(k.split("|")[1]), v[ch]) for k, v in CJK.items() if k.startswith(fam + "|"))
    for (a, va), (b, vb) in zip(scan, scan[1:]):
        if va <= stem <= vb and vb > va:
            return round(a + (b - a) * (stem - va) / (vb - va))
    raise SystemExit(f"no weight of {fam} gives a {ch} stem of {stem}")


def faces():
    css = []
    for cand, scripts in CANDS.items():
        for script, (fam, _, scale, _) in scripts.items():
            src = {"Pretendard JP Probe": "pjp/public/variable/PretendardJPVariable.ttf",
                   "Noto Sans KR Probe": "notocjk/NotoSansKR-VF.ttf",
                   "Noto Sans JP Probe": "notocjk/NotoSansJP-VF.ttf"}[fam]
            css.append(f'@font-face {{ font-family: "{cand}-{script}"; font-weight: 1 1000; '
                       f'size-adjust: {scale * 100:.1f}%; src: url("../sources/{src}"); }}')
    css.append('@font-face { font-family: "Open Sans V0"; font-weight: 300 800; font-stretch: 75% 100%; '
               'src: url("../sources/opensans/OpenSans%5Bwdth,wght%5D.ttf"); }')
    return "\n".join(css)


def params(weight):
    """Per candidate and script: [family, wght, letter-spacing em]; Latin wght."""
    out = {}
    for cand, scripts in CANDS.items():
        out[cand] = {}
        for script, (fam, ch, scale, adv) in scripts.items():
            w = wght_for(fam, ch, TARGET[(script, weight)] / scale)
            out[cand][script] = [f"{cand}-{script}", w, round(1 - adv * scale, 4)]
    out["latin"] = latin_wght(LAT[f"Segoe UI Variable Text|{weight}"])
    return out


def latin_wght(w):
    """Open Sans at wdth 95 has thinner stems than at 100; return the wght at 95
    whose `l` stem equals the wdth-100 stem at `w`."""
    path = ROOT / "sources/opensans/OpenSans[wdth,wght].ttf"

    def stem(wght, wdth):
        f = instantiateVariableFont(TTFont(path), {"wght": wght, "wdth": wdth}, updateFontNames=False)
        pen = BoundsPen(f.getGlyphSet())
        f.getGlyphSet()[f.getBestCmap()[ord("l")]].draw(pen)
        return pen.bounds[2] - pen.bounds[0]

    target, lo, hi = stem(w, 100), stem(w, 95), stem(w + 20, 95)
    return round(w + 20 * (target - lo) / (hi - lo))


HTML = """<!doctype html>
<meta charset="utf-8">
<title>v0 CJK specimen</title>
<style>
%(faces)s
body { margin: 24px; background: #fff; color: #000; font: 13px/1.4 monospace; }
h2 { font: 600 14px monospace; margin: 28px 0 6px; }
table { border-collapse: collapse; }
td { padding: 4px 12px 4px 0; vertical-align: baseline; white-space: nowrap; }
td.k { color: #666; width: 210px; }
.win { font-family: "Segoe UI Variable Text"; }
.cand { font-family: "Open Sans V0"; font-stretch: 95%%; }
</style>
<body>
<script>
const P = %(params)s;
const S = %(strings)s;
const isKo = (c) => /[\\u1100-\\u11ff\\u3130-\\u318f\\uac00-\\ud7a3]/.test(c);
const isJa = (c) => /[\\u3000-\\u303f\\u3040-\\u30ff\\u4e00-\\u9fff\\uff00-\\uffef]/.test(c);
function cand(el, name, weight, text) {
  const p = P[weight][name];
  el.className = 'cand';
  el.style.fontVariationSettings = `"wght" ${P[weight].latin}, "wdth" 95`;
  for (const run of text.match(/([\\u1100-\\u11ff\\u3130-\\u318f\\uac00-\\ud7a3]+|[\\u3000-\\u303f\\u3040-\\u30ff\\u4e00-\\u9fff\\uff00-\\uffef]+|[^\\u1100-\\u11ff\\u3130-\\u318f\\uac00-\\ud7a3\\u3000-\\u303f\\u3040-\\u30ff\\u4e00-\\u9fff\\uff00-\\uffef]+)/g)) {
    const s = document.createElement('span');
    s.textContent = run;
    const script = isKo(run[0]) ? 'ko' : isJa(run[0]) ? 'ja' : null;
    if (script) {
      const [fam, w, ls] = p[script];
      s.style.fontFamily = `"${fam}"`;
      s.style.fontVariationSettings = `"wght" ${w}`;
      s.style.letterSpacing = `${ls}em`;
    }
    el.append(s);
  }
}
const rows = [['Windows (Segoe + fallback)', null], ['Open Sans + Pretendard JP', 'pretendard'],
              ['Open Sans + Noto Sans KR/JP', 'noto']];
for (const [lang, list] of Object.entries(S)) for (const weight of [400, 700]) for (const px of [14, 20, 32]) {
  const h = document.createElement('h2');
  h.textContent = `${lang}  ${weight === 400 ? 'regular' : 'bold'}  ${px}px`;
  document.body.append(h);
  const t = document.createElement('table');
  for (const [label, name] of rows) {
    const tr = t.insertRow();
    tr.insertCell().textContent = label; tr.cells[0].className = 'k';
    const td = tr.insertCell();
    td.lang = lang;
    td.style.fontSize = px + 'px';
    const text = list.slice(0, px === 32 ? 4 : 9).join('  ·  ');
    if (name) cand(td, name, weight, text);
    else { td.className = 'win'; td.style.fontWeight = weight; td.textContent = text; }
  }
  document.body.append(t);
}
</script>
"""


def main():
    p = {w: params(w) for w in (400, 700)}
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build/specimen.html").write_text(HTML % {
        "faces": faces(), "params": json.dumps(p), "strings": json.dumps(STRINGS, ensure_ascii=False)})
    print(json.dumps(p, indent=1))


if __name__ == "__main__":
    main()
