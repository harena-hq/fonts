# SPDX-License-Identifier: Apache-2.0
"""v0.3 item 4: every built face against the Segoe face it stands for, in the
reference browser, under every feature request item 1 measured.

Per face at its Segoe weight, in DOM layout at 12, 14, 16, 20, 28 and 1000 px:
every case in data/v0_3/cases.json, with Segoe's widths from data/v0_3/segoe/<face>.json,
including the font-variant-caps cases the browser synthesizes, which the gate
cannot shape; and every base+mark text under each language, each mark after the letters of its
own script, without the coverage
pairs (a text whose composition holds a character Segoe maps and Harena UI does
not; PLAN.md v0.3), which are measured too and reported, not judged. Synthesized
caps that uppercase turn a letter into its capital, which may be such a character
(`ƒ` into U+0191): those letters are dropped from that case's text, in both fonts
alike, and the cases so trimmed are counted.

The page hashes the font bytes it loaded, which must be the built face's; it
reports how many widths it compared, which must be every case and pair; and
Segoe's live widths at 1000 px must be item 1's, within the DOM's layout unit, so
the guest's Segoe is the one measured. Tolerances are v0.2's: 0.1% of Segoe's width, or for a Small face
within one layout unit. Each face is served as a web font declared at exactly its
weight, as in v0.2's check, which is rerun separately (probe/v0_2/browser.py).

Usage: python probe/v0_3/browser.py <cdp-http-base> <repo-root-url>
Exits non-zero if any width is outside that.
"""
import base64
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, evaluate  # noqa: E402

from fontTools import unicodedata as fu  # noqa: E402

SIZES = [12, 14, 16, 20, 28, 1000]
# PLAN.md v0.2: the fifteen faces and their files, written out rather than taken from the
# build, as is the rest of what this checks: the workload is read from data/v0_3 here.
WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
EXPECTED = [(s, w) for s in ("Small", "Text", "Display") for w in WEIGHTS]


def face_name(size, w):
    return f"{size}-{WEIGHTS[w]}"


def face_path(size, w):
    return ROOT / "dist" / f"HarenaUI-{size}{WEIGHTS[w]}.ttf"


def own_script(base, mark):
    """PLAN.md v0.3 item 1: a mark of the inherited script after every letter;
    another after the letters of the scripts it is used with. The gate states the
    same rule (scripts/verify.py own_script); the two must agree."""
    return fu.script(mark) == "Zinh" or fu.script(base) in fu.script_extension(mark)
UPPERCASING = ("font-variant-caps:small-caps;", "font-variant-caps:all-small-caps;",
               "font-variant-caps:petite-caps;", "font-variant-caps:all-petite-caps;")
CGJ = "\u034F"
SEGOE_CMAP = set(json.loads((ROOT / "data/v0_1/segoe-ui-variable.json").read_text())["segoe_cmap"])


def main():
    cdp, base = sys.argv[1:3]
    page = f"{base}/probe/page.html"
    total, unit, over, info, cgj_left = 0, 0, [], [], 0
    shared = json.loads((ROOT / "data/v0_3/cases.json").read_text())
    want_cases = len(shared["cases"])
    if not want_cases or not shared["marks"]["bases"] or not shared["marks"]["marks"] \
            or shared["marks"]["langs"] != ["", "tr"] or any(not c["text"] for c in shared["cases"]):
        raise SystemExit("data/v0_3/cases.json is empty or incomplete")
    for size, w in EXPECTED:
        path = face_path(size, w)
        cmap = TTFont(path).getBestCmap()
        measured = json.loads((ROOT / f"data/v0_3/segoe/{face_name(size, w)}.json").read_text())
        doc = {"cases": [{**c, "width": wd} for c, wd in
                         zip(shared["cases"], measured["widths"], strict=True)]}
        m = shared["marks"]
        uncovered = lambda s: any(ord(ch) in SEGOE_CMAP and ord(ch) not in cmap
                                  for ch in unicodedata.normalize("NFC", s))
        cgj = {c["text"]: c["width"] for c in doc["cases"] if c["group"] == "cgj" and not c["css"]}
        before_cgj = {t[0]: cgj[t[0]] - wd for t, wd in cgj.items()
                      if len(t) == 2 and t[1] == CGJ and abs(wd - cgj[t[0]]) > 1 / 64}
        cases, trimmed = [], 0
        for c in doc["cases"]:
            text = c["text"]
            if c["features"] is None and c["css"] in UPPERCASING:  # synthesized, uppercasing
                text = "".join(ch for ch in text if not uncovered(ch.upper()))
                trimmed += text != c["text"]
            cases.append({"text": text, "css": c["css"], "lang": c["lang"]})
        pairs = [b + k for b in m["bases"] for k in m["marks"] if own_script(b, k)]
        marks = [s for s in pairs if not uncovered(s)]
        left_out = [s for s in pairs if uncovered(s)]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        url = f"{base}/{path.relative_to(ROOT)}?sha256={digest[:16]}"
        count, u = 0, 0
        for px in SIZES:  # one size per call keeps each call well inside the CDP timeout
            r = evaluate(cdp, page, "../v0_3/browser.js", {
                "font": url, "family": f"Segoe UI Variable {size}", "weight": w,
                "small": size == "Small", "sizes": [px], "cases": cases, "marks": marks,
                "langs": m["langs"], "info": left_out})
            if hashlib.sha256(base64.b64decode(r["font"])).hexdigest() != digest:
                raise SystemExit(f"{face_name(size, w)}: the page loaded other bytes than the built face")
            if len(cases) != want_cases or not marks or \
                    r["count"] != len(cases) + len(m["langs"]) * len(marks):
                raise SystemExit(f"{face_name(size, w)}: {r['count']} widths compared, not every case")
            if px == 1000:
                if len(r["segoe"]) != want_cases:
                    raise SystemExit(f"{face_name(size, w)}: {len(r['segoe'])} Segoe widths, not {want_cases}")
                shaped = [(c, s) for c, s in zip(doc["cases"], r["segoe"], strict=True)
                          if c["features"] is not None]
                if len(shaped) < want_cases // 2:
                    raise SystemExit(f"{face_name(size, w)}: too few cases to compare with item 1")
                drift = [c["text"] for c, s in shaped if abs(s - c["width"]) > 1 / 64 + 1e-9]
                if drift:
                    raise SystemExit(f"{face_name(size, w)}: Segoe's live widths differ from item 1's: {drift[:4]}")
            count, u = count + r["count"], u + r["unit"]
            # Segoe's ccmp reads CGJ, which Open Sans does not map (PLAN.md v0.3): only in
            # the group measuring that, and only after a letter it narrows here
            # with ccmp on, and by what Segoe's ccmp takes off it (two layout units of rounding)
            texts = {json.dumps(c["text"], ensure_ascii=False) for c in doc["cases"] if c["group"] == "cgj"}

            def narrowed(row):
                what, ours, theirs = row
                text = what.split(" ")[-1]
                less = sum(v * text.count(x + CGJ) for x, v in before_cgj.items())
                return text in texts and less and "'ccmp' 0" not in what \
                    and abs(ours - theirs - less) <= max(0.001 * theirs, 2000 / (64 * px))
            kept = [row for row in r["over"] if not narrowed(row)]
            cgj_left += len(r["over"]) - len(kept)
            over += [(face_name(size, w), *row) for row in kept]
            info += [(face_name(size, w), *row) for row in r["info"]
                     if abs(row[1] - row[2]) > 0.001 * row[2]]
        total, unit = total + count, unit + u
        print(f"{face_name(size, w)}: {count} measurements ({trimmed} caps cases trimmed of uncovered "
              f"capitals, {len(left_out)} coverage pairs per language reported apart), {u} within one "
              f"layout unit, {sum(1 for o in over if o[0] == face_name(size, w))} outside", flush=True)
    kinds = sorted({what.split('"')[1] for _, what, _, _ in info})
    print(f"coverage pairs differing (information, not judged): {len(info)} measurements over "
          f"{len(kinds)} texts: {' '.join(kinds)[:300]}")
    for name, what, ours, theirs in sorted(over, key=lambda o: -abs(o[2] - o[3]) / max(o[3], 1e-9))[:12]:
        print(f"  {name} {what}: {100 * (ours - theirs) / theirs:+.3f}%")
    print(f"cases before CGJ left out as coverage: {cgj_left}")
    print(f"{total} measurements; over 0.1% but within one layout unit: {unit}; outside both: "
          f"{len(over)} ->", "PASS" if not over else "FAIL")
    sys.exit(0 if not over else 1)


if __name__ == "__main__":
    main()
