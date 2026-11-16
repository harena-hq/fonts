# SPDX-License-Identifier: Apache-2.0
"""The package in Edge, and against WinUI 3, to close v0.7: its stylesheets served over HTTP from
build/npm-package (after scripts/package_npm.py).

1. Code points: every J code point outside Harena UI, alone in each J face with no language and under
   ko and ja, at 1000 px, is its data/v0_7 width for that language and weight, within half a font unit
   (the advance's rounding) and a layout unit.
2. Labels: LABELS, in each language and weight at 100 px, laid out by WinUI 3 (probe/v0_7/measure,
   unrounded) and by Edge under Segoe UI Variable Display, the face WinUI's default style draws Latin
   at that size, then the package's J Display: equal within 1 px.
3. Pairs: every pair probe/v0_7/run.py measures, under ja in J Text at each weight at 100 px, is the
   sum of its parts and its kern in data/v0_7, within one and a half font units and a layout unit: Edge
   trims no pair. A pair Unicode composes is its composed letter (PLAN.md, v0.7); a Hangul syllable
   then a sound mark is counted apart (hangul_mark).

Usage:
  python probe/v0_7/browser.py labels <cases.json>
      write the labels' cases for Measure.exe
  python probe/v0_7/browser.py <cdp-http-base> <repo-root-url> <cases.json> <widths.json>
      with Measure.exe's widths for those cases; exits non-zero on a difference
"""
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "probe/v0_7"))
from build import SIZES, WEIGHTS  # noqa: E402
from run import pair_points, points  # noqa: E402

LANGS = {"none": "", "ko-KR": "ko", "ja-JP": "ja"}
UPM = 2048
LAYOUT = 1 / 64  # Blink's layout unit, in px
LABELS = (["Settings", "設定", "設定する", "カタカナ", "설정", "Save 保存", "「設定」", "あいうえお", "、。・「」（）",
           "ひらがなとカタカナ", "한국어 설정"]
          + [s for strings in json.loads((ROOT / "probe/v0/cjk-strings.json").read_text()).values() for s in strings])
WORK = ROOT / "build/v0_7"


def label_cases():
    return [{"key": f"{lang}|{w}|{i}", "text": text, "lang": LANGS[lang] and lang, "weight": w, "size": 100}
            for lang in LANGS for w in WEIGHTS for i, text in enumerate(LABELS)]


def measure(cdp, base, groups):
    expr = WORK / "expr.js"
    pkg = f"{base}/build/npm-package"
    config = {"sheets": [f"{pkg}/ui.css", f"{pkg}/j.css"], "groups": groups}
    expr.write_text(f"const CONFIG = {json.dumps(config, ensure_ascii=False)};\n"
                    + (ROOT / "probe/v0_7/browser.js").read_text())
    res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(expr), "3600"],
                         capture_output=True, text=True, timeout=3660, check=True)
    return json.loads(res.stdout)


def composed(a, b):
    c = unicodedata.normalize("NFC", chr(a) + chr(b))
    return ord(c) if len(c) == 1 else None


def hangul_mark(a, b):
    """A Hangul syllable then a kana sound mark: the package keeps them in different files, and Edge,
    which draws a cluster from one file, takes it from Windows (as v0.6.1's mark after a Latin letter).
    The whole TTF lays it out at its parts' widths; no text writes one."""
    return unicodedata.name(chr(a)).startswith("HANGUL SYLLABLE") and b in (0x3099, 0x309A)


def main():
    if sys.argv[1] == "labels":
        Path(sys.argv[2]).write_text(json.dumps(label_cases(), ensure_ascii=False))
        return 0
    cdp, base, cases_path, widths_path = sys.argv[1:5]
    WORK.mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / "data/v0_7/winui.json").read_text())["widths"]
    differ = json.loads((ROOT / "data/v0_7/pairs.json").read_text())["differ"]
    failed = False

    cps = points()
    texts = [chr(c) for c in cps]
    measured, off = 0, []
    for size in SIZES:
        for w in WEIGHTS:
            font = f'{w} 1000px "Harena UI J {size}"'
            got = measure(cdp, base, [{"font": font, "lang": tag, "texts": texts} for tag in LANGS.values()])
            for lang, widths in zip(LANGS, got):
                for c, px in zip(cps, widths):
                    want = 10 * data[lang][str(w)][f"{c:04X}"]
                    measured += 1
                    if abs(px - want) > 1000 / UPM / 2 + LAYOUT:
                        off.append((size, w, lang, f"U+{c:04X}", px, want))
            print("code points", size, w, measured, len(off), flush=True)
    print(f"1. code points: {measured} measured, {len(off)} off their width", off[:6])
    failed |= bool(off)

    cases = json.loads(Path(cases_path).read_text())
    if cases != label_cases():
        print("the label cases are not this checkout's", file=sys.stderr)
        return 1
    winui = json.loads(Path(widths_path).read_text(encoding="utf-8-sig"))
    stack = '"Segoe UI Variable Display", "Segoe UI", "Harena UI J Display"'
    groups = [{"font": f"{w} 100px {stack}", "lang": tag, "texts": LABELS} for lang, tag in LANGS.items() for w in WEIGHTS]
    got = measure(cdp, base, groups)
    apart, worst = [], 0
    for (lang, w), widths in zip([(lang, w) for lang in LANGS for w in WEIGHTS], got):
        for i, px in enumerate(widths):
            ref = winui[f"{lang}|{w}|{i}"]
            worst = max(worst, abs(px - ref))
            if abs(px - ref) > 1:
                apart.append((lang, w, LABELS[i], px, ref))
    print(f"2. labels: {len(cases)} measured, {len(apart)} apart by more than 1 px (most {worst:.3f} px)", apart[:6])
    failed |= bool(apart)

    pairs = pair_points()
    texts = [chr(a) + chr(b) for a, b in pairs]
    trimmed, worst, apart_files = [], 0, 0
    for w in WEIGHTS:
        [widths] = measure(cdp, base, [{"font": f'{w} 100px "Harena UI J Text"', "lang": "ja", "texts": texts}])
        parts, kern = data["ja-JP"][str(w)], differ.get("ja-JP", {}).get(str(w), {})
        for (a, b), px in zip(pairs, widths):
            c = composed(a, b)
            want = (parts[f"{c:04X}"] if c else
                    parts[f"{a:04X}"] + parts[f"{b:04X}"] + kern.get(f"{a:04X}+{b:04X}", 0))
            if abs(px - want) <= 100 / UPM * 1.5 + LAYOUT:
                continue
            if hangul_mark(a, b):
                apart_files += 1
            else:
                worst = max(worst, abs(px - want))
                trimmed.append((w, f"U+{a:04X}+U+{b:04X}", px, want))
    print(f"3. pairs under ja: {len(pairs) * len(WEIGHTS)} measured, {len(trimmed)} off (most {worst:.3f} px);"
          f" {apart_files} a Hangul syllable and a sound mark, drawn from Windows", trimmed[:6])
    failed |= bool(trimmed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
