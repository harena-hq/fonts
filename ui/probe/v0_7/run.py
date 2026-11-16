# SPDX-License-Identifier: Apache-2.0
"""The widths WinUI 3 lays out Harena UI J's CJK at: every J code point outside Harena UI, in each
language and weight, at 100 px, measured by probe/v0_7/measure (a WinUI 3 app laying each out as a
TextBlock in the default style, unrounded) on the guest.

  python probe/v0_7/run.py cases <cases.json>
      write the cases for Measure.exe
  python probe/v0_7/run.py collect <cases.json> <widths.json> <provenance.json>
      check Measure.exe's output against the cases, and, rounded up as layout rounding does, against
      the Gallery's whole pixels (data/v0_7/gallery.json); write data/v0_7/winui.json
  python probe/v0_7/run.py pairs <dir>
  python probe/v0_7/run.py pairs-collect <dir>
      the same for pairs of J code points, against the sum of their parts in data/v0_7/winui.json;
      write data/v0_7/pairs.json, the pairs that differ. The cases are written in parts of PART,
      pc00.json and on, each for its own Measure.exe run (one process laying out them all runs out
      of memory); each run's widths are read from the part's name with a "w" before it.

Numbers only come back: widths in px, per code point as hex, per language ("" for none) and weight.
A TextBlock leaves a line's trailing space out of its width, so a space is measured between two
ideographs, less the two alone.
"""
import json
import math
import sys
from pathlib import Path

from fontTools import unicodedata
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build import WEIGHTS, face_path  # noqa: E402
from build_j import face_path_j  # noqa: E402

LANGS = ("", "ko-KR", "ja-JP")
SIZE = 100
PART = 200_000
KANA = ("Hiragana", "Katakana", "Katakana Phonetic Extensions", "CJK Symbols and Punctuation",
        "Halfwidth and Fullwidth Forms")
FRAME = "\u4e00"


def points():
    """J's code points outside Harena UI; the same in every face, as build_web's chunks are."""
    sets = {tuple(sorted(set(TTFont(face_path_j("Text", w), lazy=True).getBestCmap())
                         - set(TTFont(face_path("Text", w), lazy=True).getBestCmap()))) for w in WEIGHTS}
    assert len(sets) == 1, "weights cover different code points"
    return list(sets.pop())


def key(lang, w, c):
    return f"{lang}|{w}|{c:04X}"


def space(c):
    return unicodedata.category(chr(c)) == "Zs"


def cases():
    out = []
    for lang in LANGS:
        for w in WEIGHTS:
            out.append({"key": f"{lang}|{w}|frame", "text": FRAME * 2, "lang": lang, "weight": w, "size": SIZE})
            out += [{"key": key(lang, w, c), "text": FRAME + chr(c) + FRAME if space(c) else chr(c), "lang": lang,
                     "weight": w, "size": SIZE} for c in points()]
    return out


def width(widths, lang, w, c):
    return widths[key(lang, w, c)] - (widths[f"{lang}|{w}|frame"] if space(c) else 0)


def pair_points():
    """Every pair of kana and CJK punctuation, each of those with a sample of Han and Hangul either
    side, and each adjacent pair of J code points in the v0.3 and v0.4 strings; no spaces, which a
    TextBlock leaves out at a line's end."""
    from verify_web import strings
    j = [c for c in points() if not space(c)]
    near = [c for c in j if unicodedata.block(chr(c)) in KANA]
    han = [c for c in j if unicodedata.block(chr(c)) == "CJK Unified Ideographs"][::400]
    hangul = [c for c in j if unicodedata.block(chr(c)) == "Hangul Syllables"][::250]
    pairs = {(a, b) for a in near for b in near}
    pairs |= {p for a in near for b in han + hangul for p in ((a, b), (b, a))}
    pairs |= {(ord(a), ord(b)) for t in strings() for a, b in zip(t, t[1:]) if {ord(a), ord(b)} <= set(j)}
    return sorted(pairs)


def pair_key(lang, w, a, b):
    return f"{lang}|{w}|{a:04X}+{b:04X}"


def pair_cases():
    return [{"key": pair_key(lang, w, a, b), "text": chr(a) + chr(b), "lang": lang, "weight": w, "size": SIZE}
            for lang in LANGS for w in WEIGHTS for a, b in pair_points()]


def collect_pairs(case_list, widths):
    single = json.loads((ROOT / "data/v0_7/winui.json").read_text())["widths"]
    differ = {}
    for lang in LANGS:
        for w in WEIGHTS:
            parts = single[lang or "none"][str(w)]
            for a, b in pair_points():
                delta = widths[pair_key(lang, w, a, b)] - parts[f"{a:04X}"] - parts[f"{b:04X}"]
                if abs(delta) > 1e-6:
                    differ.setdefault(lang or "none", {}).setdefault(str(w), {})[f"{a:04X}+{b:04X}"] = delta
    data = {"provenance": "as data/v0_7/winui.json", "size": SIZE, "pairs": len(pair_points()),
            "differ": differ}
    (ROOT / "data/v0_7/pairs.json").write_text(json.dumps(data, indent=1) + "\n")
    print(len(case_list), "pairs;", {l: {w: len(v) for w, v in d.items()} for l, d in differ.items()} or "none differ")
    return 0


def main():
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "cases":
        Path(args[0]).write_text(json.dumps(cases(), ensure_ascii=False))
        return 0
    if mode == "pairs":
        cases_ = pair_cases()
        for i in range(0, len(cases_), PART):
            (Path(args[0]) / f"pc{i // PART:02d}.json").write_text(json.dumps(cases_[i:i + PART], ensure_ascii=False))
        return 0
    if mode == "pairs-collect":
        parts = sorted(Path(args[0]).glob("pc*.json"))
        case_list = [c for part in parts for c in json.loads(part.read_text())]
        widths = {}
        for part in parts:
            widths.update(json.loads((part.parent / ("w" + part.name)).read_text(encoding="utf-8-sig")))
    else:
        case_list = json.loads(Path(args[0]).read_text())
        widths = json.loads(Path(args[1]).read_text(encoding="utf-8-sig"))
    if case_list != (pair_cases() if mode == "pairs-collect" else cases()):
        print("the cases are not this checkout's", file=sys.stderr)
        return 1
    missing = [c["key"] for c in case_list if not isinstance(widths.get(c["key"]), (int, float))]
    if missing or len(widths) != len(case_list):
        print(f"{len(missing)} cases unmeasured, {len(widths)} widths for {len(case_list)} cases", file=sys.stderr)
        return 1
    if mode == "pairs-collect":
        return collect_pairs(case_list, widths)
    out = {lang or "none": {str(w): {f"{c:04X}": width(widths, lang, w, c) for c in points()} for w in WEIGHTS}
           for lang in LANGS}
    gallery = json.loads((ROOT / "data/v0_7/gallery.json").read_text())["widths"]
    lang_of = {"none": "none", "ko": "ko-KR", "ja": "ja-JP"}
    unlike = [(lang, w, c, px, out[lang_of[lang]][w][c]) for lang, by_w in gallery.items()
              for w, by_c in by_w.items() for c, px in by_c.items()
              if math.ceil(out[lang_of[lang]][w][c] - 1e-9) != px]
    if unlike:
        print("unlike the Gallery:", unlike, file=sys.stderr)
        return 1
    data = {"provenance": json.loads(Path(args[2]).read_text()), "size": SIZE, "widths": out}
    (ROOT / "data/v0_7").mkdir(exist_ok=True)
    (ROOT / "data/v0_7/winui.json").write_text(json.dumps(data, indent=1) + "\n")
    print(len(case_list), "widths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
