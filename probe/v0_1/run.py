# SPDX-License-Identifier: Apache-2.0
"""Measure v0.1's Segoe targets on the reference browser; write data/v0_1/.

1. The target set: every code point both Segoe UI Variable and Open Sans map,
   less Private Use, marks (M*) and format and control characters (C*). A mark
   measured alone is drawn on an inserted dotted circle, so its advance is not
   the font's. Segoe's own map comes from cmap.ps1, run on the Windows machine,
   and is passed in as a file of decimal code points.
2. Advances and pixel ink for the target set, in all 12 named instances (the v0
   comparison over the full set).
3. Pair kerning in Text 400 for every ordered pair of the set's letters,
   numbers, punctuation, symbols and space.

Usage: python probe/v0_1/run.py <cdp-http-base> <repo-root-url> <provenance.json> <segoe-cmap.txt>
"""
import json
import sys
import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, SEGOE, WEIGHTS, evaluate  # noqa: E402

OPEN_SANS = ROOT / "sources/opensans/OpenSans[wdth,wght].ttf"
STRINGS = json.loads((ROOT / "probe/v0/strings.json").read_text())


def target_set(segoe):
    both = segoe & set(TTFont(OPEN_SANS).getBestCmap())
    return sorted(c for c in both if not 0xE000 <= c <= 0xF8FF
                  and unicodedata.category(chr(c))[0] not in "MC")


def main():
    cdp, base, prov, cmap_file = sys.argv[1:5]
    provenance = json.loads(Path(prov).read_text())
    segoe = {int(x) for x in Path(cmap_file).read_text().split()}
    target = target_set(segoe)
    page = f"{base}/probe/page.html"
    out = ROOT / "data/v0_1"
    out.mkdir(parents=True, exist_ok=True)

    fams = [[f, w] for f in SEGOE for w in WEIGHTS]
    adv = evaluate(cdp, page, "measure.js", {"families": fams, "glyphs": target, "pairs": [],
                                             "strings": STRINGS})
    ink = evaluate(cdp, page, "ink.js", {"families": fams, "glyphs": target})
    instances = {k: {"advance": {cp: r[0] for cp, r in v["glyphs"].items()}, "ink": ink[k],
                     "strings": v["strings"]} for k, v in adv.items()}

    pairs = [c for c in target if unicodedata.category(chr(c))[0] in "LNPSZ"]
    kern = evaluate(cdp, page, "measure.js", {"families": [["Segoe UI Variable Text", 400]],
                                              "glyphs": pairs, "pairs": pairs, "strings": {}})
    instances["Segoe UI Variable Text|400"]["kern"] = kern["Segoe UI Variable Text|400"]["kern"]

    method = ("advances, kerning, strings: canvas measureText at 1000 px, fontKerning normal; "
              "ink: pixel edges at 1000 px; cmap: cmap.ps1 on the Windows machine")
    doc = {"provenance": {**provenance, "method": method}, "unit": "px at 1000 px font size",
           "segoe_cmap": sorted(segoe), "target": target, "kern_pairs_from": pairs,
           "instances": instances}
    (out / "segoe-ui-variable.json").write_text(json.dumps(doc, indent=0, sort_keys=True) + "\n")
    print(f"target {len(target)} code points; kern pairs measured {len(pairs) ** 2}, "
          f"kept {len(instances['Segoe UI Variable Text|400']['kern'])}")


if __name__ == "__main__":
    main()
