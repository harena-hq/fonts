# SPDX-License-Identifier: Apache-2.0
"""The package in Edge, to close v0.6: its stylesheets served over HTTP from build/npm-package.

1. Widths: every string of the v0.3 and v0.4 cases, in every Harena UI and Harena UI J face, with no
   language and under ko and ja, at 1000 px: DOM width in the package's family equals the width with
   the face's whole TTF. The TTFs' widths against Segoe's are v0.2-v0.4's batteries.
2. Line boxes: every J code point outside Harena UI after "A", at 14 and 40 px, in each J face and
   language, under the Segoe stack alone and with the package's family after it. With no language a
   difference is allowed only where Windows draws the character from another face than its chunk's
   (data/v0_6/fallback.json); under ko and ja the differences are counted.
3. Fetches: what a page fetches for a text, from its resource list.

Exits non-zero on a width difference, an unexpected line box or an unexpected fetch.
Usage: python probe/v0_6/browser.py <cdp-http-base> <repo-root-url>  (after scripts/package_npm.py)
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build import SIZES, WEIGHTS, face_path  # noqa: E402
from build_j import face_path_j  # noqa: E402
from verify_web import strings  # noqa: E402

LANGS = ["", "ko", "ja"]
WORK = ROOT / "build/v0_6"


def segoe(size):
    return f'"Segoe UI Variable {size}", "Segoe UI"'


def run(cdp, base, config, seconds=1800):
    expr = WORK / "package-expr.js"
    expr.write_text(f"const CONFIG = {json.dumps(config)};\n" + (ROOT / "probe/v0_6/package.js").read_text())
    res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(expr), str(seconds)],
                         capture_output=True, text=True, timeout=seconds + 60, check=True)
    return json.loads(res.stdout)


def main():
    cdp, base = sys.argv[1:3]
    WORK.mkdir(parents=True, exist_ok=True)
    pkg = f"{base}/build/npm-package"
    sheets = [f"{pkg}/ui.css", f"{pkg}/j.css", f"{pkg}/icons.css"]
    failed = False

    texts = strings()
    measured, differs = 0, []
    for size in SIZES:
        for w in WEIGHTS:
            for family, ttf in ((f"Harena UI {size}", face_path(size, w)), (f"Harena UI J {size}", face_path_j(size, w))):
                out = run(cdp, base, {"sheets": sheets, "mode": "widths", "strings": texts, "langs": LANGS, "px": 1000,
                                      "faces": [{"family": family, "weight": w, "ttf": f"{base}/{ttf.relative_to(ROOT)}"}]})
                measured += out["measured"]
                differs += out["differs"]
            print("widths", size, w, measured, len(differs), flush=True)
    print(f"1. widths: {measured} measured, {len(differs)} differ", differs[:6])
    failed |= bool(differs)

    fallback = json.loads((ROOT / "data/v0_6/fallback.json").read_text())
    points = sorted(set(TTFont(face_path_j("Text", 400), lazy=True).getBestCmap())
                    - set(TTFont(face_path("Text", 400), lazy=True).getBestCmap()))
    lines, unexpected, counted = 0, [], Counter()
    for size in SIZES:
        for w in WEIGHTS:
            out = run(cdp, base, {"sheets": sheets, "mode": "lines", "points": points, "langs": LANGS, "sizes": [14, 40],
                                  "faces": [{"family": f"Harena UI J {size}", "stack": segoe(size), "weight": w}]})
            lines += out["measured"]
            others = fallback["others"][str(w)]
            for key, bad in out["differs"].items():
                _, _, lang, px = key.split("|")
                if lang == "":
                    surprise = [c for c in bad if f"{c:04X}" not in others]
                    unexpected += [(size, w, px, f"U+{c:04X}") for c in surprise]
                    counted["no language, drawn by another face"] += len(bad) - len(surprise)
                else:
                    counted[f"{lang} at {px} px"] += len(bad)
            print("lines", size, w, lines, len(unexpected), flush=True)
    print(f"2. line boxes: {lines} measured, {len(unexpected)} unexpected", unexpected[:8])
    print("   counted, over 15 faces:", dict(counted))
    failed |= bool(unexpected)

    harena_j, harena = '"Harena UI J Text"', '"Harena UI Text"'
    cases = [
        ("Latin, Harena UI alone", harena, "", "Settings", {"HarenaUI-TextRegular.woff2"}),
        ("Latin, after Segoe", f"{segoe('Text')}, {harena_j}", "", "Settings", set()),
        ("icons, after Segoe", '"Segoe Fluent Icons", "Segoe MDL2 Assets", "Harena UI Icons"', "", "", set()),
        ("icons, alone", '"Harena UI Icons"', "", "", {"HarenaUIIcons-Regular.woff2"}),
        ("Hangul, after Segoe", f"{segoe('Text')}, {harena_j}", "ko", "한국어 설정", {"HarenaUIJ-TextRegular-hangul-1.woff2"}),
        ("Hangul with a rare syllable", f"{segoe('Text')}, {harena_j}", "ko", "똠방각하",
         {"HarenaUIJ-TextRegular-hangul-1.woff2", "HarenaUIJ-TextRegular-hangul-2a.woff2"}),
        ("Hangul, J alone", harena_j, "ko", "한국어 설정",
         {"HarenaUI-TextRegular.woff2", "HarenaUIJ-TextRegular-hangul-1.woff2"}),
    ]
    wrong = []
    for name, stack, lang, text, want in cases:
        got = set(run(cdp, base, {"sheets": sheets, "mode": "fetch",
                                  "text": {"stack": stack, "weight": 400, "lang": lang, "text": text}}, 120))
        print(f"   {name}: {sorted(got) or 'nothing'}")
        if got != want:
            wrong.append((name, sorted(got), sorted(want)))
    print(f"3. fetches: {len(cases)} pages, {len(wrong)} unexpected", wrong)
    failed |= bool(wrong)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
