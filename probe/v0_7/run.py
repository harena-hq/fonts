# SPDX-License-Identifier: Apache-2.0
"""The widths WinUI 3 lays out Harena UI J's CJK at: every J code point outside Harena UI, in each
language and weight, at 100 px, measured by probe/v0_7/measure (a WinUI 3 app laying each out as a
TextBlock in the default style, unrounded) on the guest.

  python probe/v0_7/run.py cases <cases.json>
      write the cases for Measure.exe
  python probe/v0_7/run.py collect <cases.json> <widths.json> <provenance.json>
      check Measure.exe's output against the cases, and, rounded up as layout rounding does, against
      the Gallery's whole pixels (data/v0_7/gallery.json); write data/v0_7/winui.json

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


def main():
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "cases":
        Path(args[0]).write_text(json.dumps(cases(), ensure_ascii=False))
        return 0
    case_list = json.loads(Path(args[0]).read_text())
    if case_list != cases():
        print("the cases are not this checkout's", file=sys.stderr)
        return 1
    widths = json.loads(Path(args[1]).read_text(encoding="utf-8-sig"))
    missing = [c["key"] for c in case_list if not isinstance(widths.get(c["key"]), (int, float))]
    if missing or len(widths) != len(case_list):
        print(f"{len(missing)} cases unmeasured, {len(widths)} widths for {len(case_list)} cases", file=sys.stderr)
        return 1
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
