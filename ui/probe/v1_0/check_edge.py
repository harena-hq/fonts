# SPDX-License-Identifier: Apache-2.0
"""1.0 item 2: Edge's file from probe/v1_0/collect.py gives v0.6.1's and v0.7's Edge results.

From v0.6 and v0.6.1 (probe/v0_6/browser.py):
1. widths: each string in the package's family is its width in the face's whole TTF, exactly; a string
   of conjoining jamo in Semibold is counted apart, and must differ: J maps no jamo, so the package
   leaves them to the system's fonts, while the whole TTF composes them into a syllable J has, 2%
   wider in Semibold;
2. line boxes: "A", and "A" and each J code point, with J after the Segoe stack, is the height of "A"
   alone;
3. fetches: each of the nine pages fetches exactly the files it did.
From v0.7 (probe/v0_7/browser.py):
4. code points: each is its data/v1_0 width for its language and weight, within half a font unit and
   a layout unit;
5. labels: within 1 px of WinUI 3's (data/v1_0/labels.json, probe/v0_7/measure);
6. pairs under ja: each is the sum of its parts and its kern, within one and a half font units and a
   layout unit; a Hangul syllable then a sound mark is counted apart.

Usage: python probe/v1_0/check_edge.py <edge.json>; exits non-zero on a difference.
"""
import json
import sys
import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "probe/v0_7"), str(ROOT / "probe/v1_0")]
from browser import composed, hangul_mark, label_cases  # noqa: E402
from collect import artifacts, complete, digest, fetch_cases, inputs  # noqa: E402

UPM = 2048
JAMO = [(0x1100, 0x11FF), (0xA960, 0xA97F), (0xD7B0, 0xD7FF)]


def jamo(s, mapped):
    """Conjoining jamo, which J does not map, composing into syllables it does."""
    has = any(lo <= ord(c) <= hi for c in s for lo, hi in JAMO)
    unmapped = {ord(c) for c in s} - mapped
    composed = {ord(c) for c in unicodedata.normalize("NFC", s)}
    return has and all(any(lo <= c <= hi for lo, hi in JAMO) for c in unmapped) and composed <= mapped
LAYOUT = 1 / 64
WINUI_LANG = {"none": "none", "ko": "ko-KR", "ja": "ja-JP"}


def main():
    r = json.loads(Path(sys.argv[1]).read_text())
    inp = inputs()
    if r["inputs"] != {k: digest(v) for k, v in inp.items()} | {"artifacts": artifacts(inp)}:
        sys.exit("measured from other cases, probe, package or TTFs")
    missing = complete(r, inp)
    if missing:
        sys.exit(f"incomplete: {len(missing)} keys missing or malformed, {missing[:6]}")
    failed = False

    j = set(TTFont(ROOT / "dist/HarenaUIJ-TextRegular.ttf", lazy=True).getBestCmap())
    differ, measured, system, expected = [], 0, 0, 0
    for key, ours in r["widths"].items():
        if key.endswith("|alone"):
            whole = r["widths"][key[: -len("alone")] + "ttf"]
            measured += len(ours)
            # only in Semibold do the syllables J has differ from the system's jamo (v0.7 made them 2%
            # wider there, as WinUI 3 draws Malgun Gothic, which has no Semibold)
            counted = key.startswith("Harena UI J|") and key.split("|")[2] == "600"
            for s, a, b in zip(inp["strings"], ours, whole):
                expected += counted and jamo(s, j)
                if a == b:
                    continue
                if counted and jamo(s, j):
                    system += 1
                else:
                    differ.append((key, s, a, b))
    print(f"1. widths: {measured} measured, {len(differ)} differ; {system} of {expected} expected of conjoining jamo"
          " in Semibold",
          differ[:6])
    failed |= bool(differ) or system != expected

    differ, measured = [], 0
    for key, ours in r["lines"].items():
        if key.endswith("|ours"):
            [alone] = r["lines"][key[: -len("ours")] + "alone"]
            [latin] = r["lines"][key[: -len("ours")] + "latin"]
            measured += len(ours) + 1
            differ += [(key, f"U+{c:04X}") for c, h in zip(inp["points"], ours) if h != alone]
            differ += [(key, "A") for h in [latin] if h != alone]
    print(f"2. line boxes: {measured} measured, {len(differ)} not Segoe's", differ[:8])
    failed |= bool(differ)

    wrong = [(name, r["fetches"][name], sorted(want)) for name, *_, want in fetch_cases()
             if r["fetches"][name] != sorted(want)]
    print(f"3. fetches: {len(r['fetches'])} pages, {len(wrong)} unexpected", wrong)
    failed |= bool(wrong) or len(r["fetches"]) != 9

    data = json.loads((ROOT / "data/v1_0/winui.json").read_text())["widths"]
    off, measured = [], 0
    for key, widths in r["points"].items():
        size, w, lang = key.split("|")
        for c, px in zip(inp["points"], widths):
            want = 10 * data[WINUI_LANG[lang]][w][f"{c:04X}"]
            measured += 1
            if abs(px - want) > 1000 / UPM / 2 + LAYOUT:
                off.append((key, f"U+{c:04X}", px, want))
    print(f"4. code points: {measured} measured, {len(off)} off their width", off[:6])
    failed |= bool(off) or measured != len(inp["points"]) * 45

    ref = json.loads((ROOT / "data/v1_0/labels.json").read_text())
    if ref["provenance"]["cases_sha256"] != digest(label_cases()):
        sys.exit("data/v1_0/labels.json was measured from other label cases")
    winui = ref["widths"]
    apart, worst, measured = [], 0, 0
    for key, widths in r["labels"].items():
        lang, w = key.split("|")
        for i, px in enumerate(widths):
            ref = winui[f"{WINUI_LANG[lang]}|{w}|{i}"]
            measured += 1
            worst = max(worst, abs(px - ref))
            if abs(px - ref) > 1:
                apart.append((key, inp["labels"][i], px, ref))
    print(f"5. labels: {measured} measured, {len(apart)} apart by more than 1 px (most {worst:.3f} px)", apart[:6])
    failed |= bool(apart) or measured != len(inp["labels"]) * 15

    differs = json.loads((ROOT / "data/v1_0/pairs.json").read_text())["differ"]
    trimmed, worst, counted, measured = [], 0, 0, 0
    for w, widths in r["pairs"].items():
        parts, kern = data["ja-JP"][w], differs.get("ja-JP", {}).get(w, {})
        for (a, b), px in zip(inp["pairs"], widths):
            c = composed(a, b)
            want = (parts[f"{c:04X}"] if c else
                    parts[f"{a:04X}"] + parts[f"{b:04X}"] + kern.get(f"{a:04X}+{b:04X}", 0))
            measured += 1
            if abs(px - want) <= 100 / UPM * 1.5 + LAYOUT:
                continue
            if hangul_mark(a, b):
                counted += 1
            else:
                worst = max(worst, abs(px - want))
                trimmed.append((w, f"U+{a:04X}+U+{b:04X}", px, want))
    print(f"6. pairs under ja: {measured} measured, {len(trimmed)} off (most {worst:.3f} px);"
          f" {counted} a Hangul syllable and a sound mark", trimmed[:6])
    failed |= bool(trimmed) or measured != len(inp["pairs"]) * 5
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
