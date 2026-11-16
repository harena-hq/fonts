# SPDX-License-Identifier: Apache-2.0
"""Analyse data/v0/ against candidate Latin sources; print what docs/v0-feasibility.md reports.

Segoe numbers come from the browser (data/v0). Candidate numbers come from the
font files, instanced with fontTools and shaped with HarfBuzz; method_check()
is the evidence that the two agree.

Usage: python probe/v0/analyze.py [--detail]
"""
import functools
import json
import statistics as st
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = [350, 400, 600, 700]
OPSZ = ["Small", "Text", "Display"]
INSTANCES = [(o, w) for o in OPSZ for w in WEIGHTS]
# U+00AD is a format character the shaper hides; there is nothing to compare.
SKIP = {173}
GLYPHS = [cp for cp in list(range(0x20, 0x7F)) + list(range(0xA0, 0x100)) if cp not in SKIP]
# Overlap is counted where a glyph's ink would cross its advance by this much
# more than Segoe's own glyph does. Pixel ink is good to about 0.5 px.
OVERLAP_PX = 5

SELAWIK = {350: "selawksl", 400: "selawk", 600: "selawksb", 700: "selawkb"}
CANDIDATES = {
    # name: (probe family, file or per-weight files, wdth values to try)
    "Inter (Pretendard JP)": ("Pretendard JP Probe", "pjp/public/variable/PretendardJPVariable.ttf", [100]),
    "Open Sans": ("Open Sans Probe", "opensans/OpenSans[wdth,wght].ttf", [100, 95, 90, 85]),
    "Noto Sans": ("Noto Sans Probe", "notosans/NotoSans[wdth,wght].ttf", [100, 95, 90, 85]),
    "Selawik": ("Selawik Probe", None, [100]),
}

load = lambda n: json.loads((ROOT / "data/v0" / f"{n}.json").read_text())
SEG = load("segoe-ui-variable")["instances"]
STEMS = load("stems")
STRINGS = [s for g in json.loads((ROOT / "probe/v0/strings.json").read_text()).values() for s in g]
seg = lambda o, w: SEG[f"Segoe UI Variable {o}|{w}"]


def ink_x(font, glyph):
    """Tight horizontal ink bounds of the outline. `glyf.recalcBounds` would bound
    the off-curve points too, which overstates a curve's extent by up to 8 px."""
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[glyph].draw(pen)
    return None if pen.bounds is None else (pen.bounds[0], pen.bounds[2])


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, int(p * (len(xs) - 1) + 0.5)))]


@functools.lru_cache(maxsize=None)
def face(cand, o, w, wdth):
    """Advances and ink per code point, and kerned string widths, px at 1000 px."""
    fam, path, _ = CANDIDATES[cand]
    if path is None:
        path, loc = f"selawik/{SELAWIK[w]}.ttf", {}
        wght = w
    else:
        wght = STEMS["matched_wght"][fam][f"Segoe UI Variable {o}|{w}"]
        loc = {"wght": wght, "wdth": wdth}
    src = ROOT / "sources" / path
    f = TTFont(src)
    if loc:
        loc = {k: v for k, v in loc.items() if k in {a.axisTag for a in f["fvar"].axes}}
        f = instantiateVariableFont(f, loc, updateFontNames=False)
    k = 1000 / f["head"].unitsPerEm
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    adv, ink = {}, {}
    for cp in GLYPHS:
        if cp not in cmap:
            continue
        g = cmap[cp]
        adv[cp] = hmtx[g][0] * k
        b = ink_x(f, g)
        if b:
            ink[cp] = (b[0] * k, b[1] * k)
    blob = hb.Blob.from_file_path(str(src))
    hf = hb.Font(hb.Face(blob))
    if loc:
        hf.set_variations(loc)
    widths = {}
    for s in STRINGS:
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(hf, buf, {"kern": True})
        widths[s] = sum(p.x_advance for p in buf.glyph_positions) * k
    return {"wght": wght, "adv": adv, "ink": ink, "strings": widths}


def method_check():
    print("## Method check: the browser against fontTools, Pretendard JP at wght 400")
    chk = load("method-check")["instances"]["Pretendard JP Probe|400"]
    f = instantiateVariableFont(TTFont(ROOT / "sources/pjp/public/variable/PretendardJPVariable.ttf"),
                                {"wght": 400}, updateFontNames=False)
    k = 1000 / f["head"].unitsPerEm
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    dadv, dl, dr = [], [], []
    for cp in GLYPHS:
        g = cmap[cp]
        dadv.append(abs(chk["advance"][str(cp)] - hmtx[g][0] * k))
        b, row = ink_x(f, g), chk["ink"][str(cp)]
        if b and row:
            dl.append(row[0] - b[0] * k)
            dr.append(row[1] - b[1] * k)
    ok = max(dadv) <= 0.01
    print(f"advance |diff| max {max(dadv):.3f} px -> {'PASS' if ok else 'FAIL'} (tolerance 0.01)")
    for n, x in (("left", dl), ("right", dr)):
        print(f"ink {n:5} diff median {st.median(x):+.2f}  p5 {q(x, .05):+.2f}  p95 {q(x, .95):+.2f}  "
              f"min {min(x):+.2f}  max {max(x):+.2f}")
    return ok


def compare(cand, o, w, wdth):
    s, c = seg(o, w), face(cand, o, w, wdth)
    adv, inkr, kept, over = [], [], [], []
    for cp in GLYPHS:
        key = str(cp)
        if cp not in c["adv"] or cp not in c["ink"] or not s["ink"].get(key):
            continue
        sa, (sl, sr) = s["advance"][key], s["ink"][key][:2]
        ca, (cl, cr) = c["adv"][cp], c["ink"][cp]
        adv.append(sa / ca)
        inkr.append((sr - sl) / (cr - cl))
        own = ca - (cr - cl)        # the candidate's own total sidebearing
        left = sa - (cr - cl)       # what it would get inside Segoe's advance
        segoe = sa - (sr - sl)      # what Segoe gives its own glyph
        if own > 1:
            kept.append(left / own)
        if left < min(segoe, 0) - OVERLAP_PX:
            over.append(chr(cp))
    serr = [100 * (c["strings"][x] - s["strings"][x][0]) / s["strings"][x][0] for x in STRINGS]
    return {"wght": c["wght"], "adv": adv, "ink": inkr, "kept": kept, "over": over, "serr": serr,
            "missing": len(GLYPHS) - len(c["adv"])}


def summary():
    print("\n## Candidates, all 12 Segoe instances pooled (glyph medians are per instance, then median)")
    print(f"{'candidate':24} {'wdth':>4}  {'adv S/C':>8} {'ink S/C':>8} {'kept p50':>8} {'kept p5':>8} "
          f"{'overlaps':>8} {'str err':>8} {'worst':>7}")
    for cand, (_, _, wdths) in CANDIDATES.items():
        for wd in wdths:
            rs = [compare(cand, o, w, wd) for o, w in INSTANCES]
            med = lambda f: st.median(f(r) for r in rs)
            print(f"{cand:24} {wd:>4}  {med(lambda r: st.median(r['adv'])):8.3f} "
                  f"{med(lambda r: st.median(r['ink'])):8.3f} {med(lambda r: st.median(r['kept'])):8.3f} "
                  f"{med(lambda r: q(r['kept'], .05)):8.3f} {med(lambda r: len(r['over'])):8.1f} "
                  f"{med(lambda r: st.mean(r['serr'])):+8.2f} {max((x for r in rs for x in r['serr']), key=abs):+7.2f}")


def detail(cand, wd):
    print(f"\n## {cand}, wdth {wd}, per Segoe instance")
    for o, w in INSTANCES:
        r = compare(cand, o, w, wd)
        print(f"{o:7} {w}  wght {r['wght']:>4}  adv {st.median(r['adv']):.3f} [{q(r['adv'], .05):.3f}, "
              f"{q(r['adv'], .95):.3f}]  ink {st.median(r['ink']):.3f}  kept {st.median(r['kept']):.3f} "
              f"p5 {q(r['kept'], .05):+.3f}  str {st.mean(r['serr']):+.2f}%  overlaps: {''.join(r['over']) or '-'}"
              + (f"  missing {r['missing']}" if r["missing"] else ""))


def stems():
    print("\n## Stems of l (px at 1000 px) and stem-matched weight")
    st_ = STEMS["stems"]
    for o, w in INSTANCES:
        key = f"Segoe UI Variable {o}|{w}"
        m = "  ".join(f"{c.split(' Probe')[0]} {STEMS['matched_wght'][c][key]}" for c in STEMS["matched_wght"]
                      if not c.startswith("Selawik"))
        sel = st_.get(f"Selawik Probe|{w}", {}).get("l")
        print(f"{o:7} {w}  l {st_[key]['l']:6.2f}   {m}   Selawik {w}: l {sel}")


def opsz():
    print("\n## Segoe opsz instances against Text, same weight (pixel ink)")
    for w in WEIGHTS:
        t = seg("Text", w)
        for o in ("Small", "Display"):
            g = seg(o, w)
            keys = [str(cp) for cp in GLYPHS if t["ink"].get(str(cp)) and g["ink"].get(str(cp))]
            adv = [g["advance"][k] / t["advance"][k] for k in keys]
            ink = [(g["ink"][k][1] - g["ink"][k][0]) / (t["ink"][k][1] - t["ink"][k][0]) for k in keys]
            print(f"{w} {o:7}  advance median {st.median(adv):.3f} [{q(adv, .05):.3f}, {q(adv, .95):.3f}]"
                  f"   ink width median {st.median(ink):.3f} [{q(ink, .05):.3f}, {q(ink, .95):.3f}]")


def selawik_compat():
    print("\n## Selawik: can its five weights interpolate?")
    names = ["selawkl", "selawksl", "selawk", "selawksb", "selawkb"]
    fonts = {n: TTFont(ROOT / "sources/selawik" / f"{n}.ttf") for n in names}
    base = fonts["selawk"]
    order = base.getGlyphOrder()

    def shape(f, g):
        gl = f["glyf"][g]
        if gl.numberOfContours <= 0:
            return (gl.numberOfContours, len(gl.components) if gl.isComposite() else 0)
        return (gl.numberOfContours, tuple(gl.endPtsOfContours))

    bad = sum(1 for n in names if n != "selawk" for g in order
              if shape(fonts[n], g) != shape(base, g))
    print(f"{len(order)} glyphs ({len(base.getBestCmap())} mapped); contour structure differs from "
          f"Regular in {bad} of {len(order) * 4} glyph comparisons")


def open_sans_narrowing():
    print("\n## Open Sans: stem of l against wdth, and the wght that restores it")
    src = TTFont(ROOT / "sources/opensans/OpenSans[wdth,wght].ttf")
    k = 1000 / src["head"].unitsPerEm

    def stem(wght, wdth):
        f = instantiateVariableFont(TTFont(ROOT / "sources/opensans/OpenSans[wdth,wght].ttf"),
                                    {"wght": wght, "wdth": wdth}, updateFontNames=False)
        lo, hi = ink_x(f, f.getBestCmap()[ord("l")])
        return (hi - lo) * k

    w = STEMS["matched_wght"]["Open Sans Probe"]["Segoe UI Variable Text|400"]
    s100, s95, s95b = stem(w, 100), stem(w, 95), stem(w + 10, 95)
    per = (s95b - s95) / 10
    print(f"wght {w}: wdth 100 {s100:.2f} px, wdth 95 {s95:.2f} px ({100 * (s95 / s100 - 1):+.1f}%); "
          f"{per:.3f} px per wght unit at wdth 95, so {(s100 - s95) / per:.1f} units restore it")


def opsz_check():
    print("\n## Edge and the named instances: does size or a setting move opsz? (opsz-check.json)")
    d = load("opsz-check")["widths"]
    for key, r in d.items():
        vals = list(r.values())
        print(f"{key:36} spread {100 * (max(vals) - min(vals)) / min(vals):.3f}% over {len(vals)} conditions")


if __name__ == "__main__":
    method_check()
    stems()
    summary()
    opsz()
    opsz_check()
    selawik_compat()
    open_sans_narrowing()
    if "--detail" in sys.argv:
        for cand, (_, _, wdths) in CANDIDATES.items():
            for wd in wdths:
                detail(cand, wd)
