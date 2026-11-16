# SPDX-License-Identifier: Apache-2.0
"""The package in Edge, to close v0.6: its stylesheets served over HTTP from build/npm-package.

1. Widths: every string of the v0.3 and v0.4 cases, in every Harena UI and Harena UI J face, with no
   language and under ko and ja, at 1000 px: DOM width in the package's family equals the width with
   the face's whole TTF. The TTFs' widths against Segoe's are v0.2-v0.4's batteries.
2. Line boxes: every J code point outside Harena UI after "A", at 14 and 40 px, in each J face and
   language, with the package's family after the Segoe stack (a combining mark after "Aか"), is the
   height of "A" alone: a line is
   Segoe's height whatever it holds, as WinUI 3 draws it (v0.6.1).
3. Fetches: what a page fetches for a text, from its resource list.

Exits non-zero on a width difference, a line box not Segoe's or an unexpected fetch.
Usage: python probe/v0_6/browser.py <cdp-http-base> <repo-root-url>  (after scripts/package_npm.py)
"""
import json
import unicodedata
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build import SIZES, WEIGHTS, face_path  # noqa: E402
from build_j import face_path_j  # noqa: E402
from build_web import chunks  # noqa: E402
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

    points = sorted(set(TTFont(face_path_j("Text", 400), lazy=True).getBestCmap())
                    - set(TTFont(face_path("Text", 400), lazy=True).getBestCmap()))
    marks = [c for c in points if unicodedata.category(chr(c)).startswith("M")]
    lines, differ = 0, []
    for size in SIZES:
        for w in WEIGHTS:
            out = run(cdp, base, {"sheets": sheets, "mode": "lines", "points": points, "langs": LANGS, "sizes": [14, 40],
                                  "marks": marks,
                                  "faces": [{"family": f"Harena UI J {size}", "stack": segoe(size), "weight": w}]})
            lines += out["measured"]
            differ += [(key, f"U+{c:04X}") for key, bad in out["differs"].items() for c in bad]
            print("lines", size, w, lines, len(differ), flush=True)
    print(f"2. line boxes: {lines} measured, {len(differ)} not Segoe's", differ[:8])
    failed |= bool(differ)

    harena_j, harena = '"Harena UI J Text"', '"Harena UI Text"'
    # 鬱 is JIS X 0208 level 2: it lives in one of the other Han parts
    rare = next(n for n, p in chunks(TTFont(face_path_j("Text", 400), lazy=True).getBestCmap(),
                                     TTFont(face_path("Text", 400), lazy=True).getBestCmap()).items() if 0x9B31 in p)
    RARE = f"HarenaUIJ-TextRegular-{rare}.woff2"
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
        ("Japanese, after Segoe", f"{segoe('Text')}, {harena_j}", "ja", "設定を保存する",
         {"HarenaUIJ-TextRegular-kana.woff2", "HarenaUIJ-TextRegular-han-1.woff2"}),
        ("Japanese with a rare kanji", f"{segoe('Text')}, {harena_j}", "ja", "設定を保存する 鬱",
         {"HarenaUIJ-TextRegular-kana.woff2", "HarenaUIJ-TextRegular-han-1.woff2", RARE}),
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
