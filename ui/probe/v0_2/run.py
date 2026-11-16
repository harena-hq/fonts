# SPDX-License-Identifier: Apache-2.0
"""Measure v0.2's Segoe targets on the reference browser; write data/v0_2/.

v0.2 matches every face Edge draws from Segoe UI Variable: three optical sizes,
each at five named weights. This measures, per face, what v0.1 measured for Text
Regular alone, over v0.1's target set and pair set (data/v0_1, same Segoe file):

1. matching.json: which face each CSS weight 1-1000 draws, per size, and what
   `font-style: italic` draws (matching.js).
2. segoe/<Size>-<Weight>.json, one per face: advances, pixel ink, v0 string
   widths, pair kerning (measure.js, ink.js), the `l` and `I` stems
   (stems.js), and the digits' advances under tabular-nums in DOM layout.

Usage: python probe/v0_2/run.py <cdp-http-base> <repo-root-url> <provenance.json>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, SEGOE, evaluate  # noqa: E402

WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
STRINGS = json.loads((ROOT / "probe/v0/strings.json").read_text())
V0_1 = json.loads((ROOT / "data/v0_1/segoe-ui-variable.json").read_text())
TEXT = "Hamburgefontsiv lllll 0123456789"


def write(path, provenance, method, data):
    doc = {"provenance": {**provenance, "method": method}, "unit": "px at 1000 px font size", **data}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=0, sort_keys=True) + "\n")


def main():
    cdp, base, prov = sys.argv[1:4]
    provenance = json.loads(Path(prov).read_text())
    assert provenance["segoe_ui_variable"] == V0_1["provenance"]["segoe_ui_variable"], \
        "a different Segoe file than v0.1's target set was read from"
    page = f"{base}/probe/page.html"
    out = ROOT / "data/v0_2"

    m = evaluate(cdp, page, "../v0_2/matching.js", {"sizes": SEGOE, "weights": list(WEIGHTS),
                                                    "text": TEXT})
    write(out / "matching.json", provenance,
          "the text's width for every CSS weight 1-1000, in canvas at 1000 px and in DOM at "
          "100 px (scaled to 1000), matched exactly to a named weight's width; variation: DOM "
          "width at weight 400 under font-variation-settings 'wght' n; italic: canvas and DOM "
          "width, and the slant of `l`'s left ink edge, dx/dy between 100 and 600 px above the "
          "baseline, negative leaning forward",
          {"text": TEXT, "sizes": m})
    for fam, r in m.items():
        print(fam.removeprefix("Segoe UI Variable "), r["weights"], r["dom_weights"] == r["weights"],
              r["variation"], {w: v["slant"] for w, v in r["italic"].items()})

    target, pairs = V0_1["target"], V0_1["kern_pairs_from"]
    digits = [str(i) for i in range(10)]
    method = ("advances, kerning, strings: canvas measureText at 1000 px, fontKerning normal; "
              "ink: pixel edges at 1000 px; stems: pixel coverage along one row 250 px above "
              "the baseline at 1000 px; tabular: DOM span width at 1000 px under "
              "font-variant-numeric: tabular-nums")
    for fam in SEGOE:
        for w, name in WEIGHTS.items():
            key = f"{fam}|{w}"
            face = [[fam, w]]
            adv = evaluate(cdp, page, "measure.js", {"families": face, "glyphs": target,
                                                     "pairs": [], "strings": STRINGS})[key]
            kern = evaluate(cdp, page, "measure.js", {"families": face, "glyphs": pairs,
                                                      "pairs": pairs, "strings": {}})[key]["kern"]
            ink = evaluate(cdp, page, "ink.js", {"families": face, "glyphs": target})[key]
            stems = evaluate(cdp, page, "stems.js", {"families": face, "chars": "lI"})[key]
            tnum = evaluate(cdp, page, "../v0_1/dom.js",
                            {"families": [fam], "strings": digits, "sizes": [1000],
                             "numeric": "tabular-nums", "weight": w})
            size = fam.removeprefix("Segoe UI Variable ")
            write(out / "segoe" / f"{size}-{name}.json", provenance, method, {
                "face": {"family": fam, "weight": w},
                "advance": {cp: r[0] for cp, r in adv["glyphs"].items()},
                "ink": ink, "strings": adv["strings"], "kern": kern, "stems": stems,
                "tabular": {str(ord(d)): tnum[f"{fam}|1000|{d}"] for d in digits}})
            print(f"{size}-{name}: {len(kern)} kern pairs, stem l {stems['l']}")


if __name__ == "__main__":
    main()
