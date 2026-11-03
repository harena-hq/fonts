#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Write the web delivery from the built TTFs: one WOFF2 per Harena UI face and for Harena UI Icons,
and Harena UI J's code points outside Harena UI in chunks, each a subset of its face.

A J face is served as Harena UI's file for Harena UI's code points plus its chunks (PLAN, v0.6), so
no J file repeats the Latin. The chunks are the same code points in every face: kana with CJK and
full-width punctuation; Hangul in KS X 1001, with its jamo, and the rest; Han, with radicals and
compatibility ideographs; and the other symbols. A set too large for one file is cut in code point
order into PARTS equal parts.

Writes dist/web/*.woff2 and SHA256SUMS-Web.

Usage: python scripts/build_web.py
"""
import hashlib
import io
import sys
from pathlib import Path

from fontTools import subset, unicodedata
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import DIST, ROOT, SIZES, WEIGHTS, face_path  # noqa: E402
from build_j import face_path_j  # noqa: E402

WEB = DIST / "web"
ICONS = DIST / "HarenaUIIcons-Regular.ttf"
LIMIT = 256_000  # bytes a chunk may weigh
PARTS = {"hangul-2": 3, "han": 7}
KANA = ("Hiragana", "Katakana", "Katakana Phonetic Extensions", "CJK Symbols and Punctuation",
        "Halfwidth and Fullwidth Forms")
HAN = ("CJK Compatibility Ideographs", "Kangxi Radicals", "CJK Radicals Supplement")
SYLLABLES = (0xAC00, 0xD7A3)
# Last declared is checked first (CSS Fonts 4, 4.5): the common chunks go last.
ORDER = ("han", "kana", "symbols", "hangul-2", "hangul-1")


def _ksx1001(c):
    return len(chr(c).encode("euc_kr", "ignore")) == 2


def chunks(j_cmap, ui_cmap):
    """{name: sorted code points} for J's code points outside Harena UI, cut as PARTS says, in ORDER."""
    sets = {name: [] for name in ORDER}
    for c in sorted(set(j_cmap) - set(ui_cmap)):
        block = unicodedata.block(chr(c))
        if SYLLABLES[0] <= c <= SYLLABLES[1]:
            sets["hangul-1" if _ksx1001(c) else "hangul-2"].append(c)
        elif block == "Hangul Compatibility Jamo":
            sets["hangul-1"].append(c)
        elif block.startswith("CJK Unified Ideographs") or block in HAN:
            sets["han"].append(c)
        elif block in KANA:
            sets["kana"].append(c)
        else:
            sets["symbols"].append(c)
    out = {}
    for name, points in sets.items():
        n = PARTS.get(name, 1)
        size = -(-len(points) // n)
        for i in range(n):
            part = "abcdefg"[i] if name[-1].isdigit() else f"-{'abcdefg'[i]}"
            out[name if n == 1 else name + part] = points[i * size:(i + 1) * size]
    return out


def declared(name, points):
    """The code points a chunk is declared for, wider than it holds: a face draws only what its file
    has (CSS Fonts 4: the unicode-range meets the font's cmap), so a range may span the gaps between
    its points within a block, which keeps it short. KS X 1001's chunk, checked first, spans every
    syllable; one it lacks falls to the chunk that has it."""
    spans = {}
    for c in points:
        lo, hi = spans.setdefault(unicodedata.block(chr(c)), [c, c])
        spans[unicodedata.block(chr(c))] = [min(lo, c), max(hi, c)]
    if name == "hangul-1":
        spans["Hangul Syllables"] = list(SYLLABLES)
    return sorted({c for lo, hi in spans.values() for c in range(lo, hi + 1)})


def overrides(face):
    """A fallback face's line metrics as Edge takes them on Windows, from DirectWrite: win ascent and
    descent, and the gap hhea adds beyond them; as CSS percentages of the em."""
    upem, (ascent, descent, gap), (win_ascent, win_descent) = face["upem"], face["hhea"], face["win"]
    extra = max(0, ascent - descent + gap - win_ascent - win_descent)
    return {"ascent-override": 100 * win_ascent / upem, "descent-override": 100 * win_descent / upem,
            "line-gap-override": 100 * extra / upem}


def ui_file(size, w):
    return f"HarenaUI-{size}{WEIGHTS[w]}.woff2"


def j_file(size, w, chunk):
    return f"HarenaUIJ-{size}{WEIGHTS[w]}-{chunk}.woff2"


def subset_of(path, points):
    font = TTFont(path)
    options = subset.Options()
    options.layout_features = ["*"]
    options.layout_scripts = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.glyph_names = False
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=points)
    subsetter.subset(font)
    return font


def woff2(font):
    # The TTF's own timestamp, not the time of this build: two builds write the same bytes.
    font.recalcTimestamp = False
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def plan():
    """(file name, TTF, code points or None for the whole font), every file the delivery has."""
    files = [("HarenaUIIcons-Regular.woff2", ICONS, None)]
    for size in SIZES:
        for w in WEIGHTS:
            files.append((ui_file(size, w), face_path(size, w), None))
            j_cmap = TTFont(face_path_j(size, w), lazy=True).getBestCmap()
            ui_cmap = TTFont(face_path(size, w), lazy=True).getBestCmap()
            for name, points in chunks(j_cmap, ui_cmap).items():
                files.append((j_file(size, w, name), face_path_j(size, w), points))
    return files


def main():
    WEB.mkdir(parents=True, exist_ok=True)
    for old in WEB.glob("*.woff2"):
        old.unlink()
    sums, heavy = [], []
    for name, path, points in plan():
        data = woff2(TTFont(path) if points is None else subset_of(path, points))
        if points is not None and len(data) > LIMIT:
            heavy.append(f"{name} {len(data)}")
        (WEB / name).write_bytes(data)
        sums.append(f"{hashlib.sha256(data).hexdigest()}  dist/web/{name}\n")
        print(name, len(data), flush=True)
    if heavy:
        print("over the chunk limit:", *heavy, file=sys.stderr)
        return 1
    (ROOT / "SHA256SUMS-Web").write_text("".join(sums))
    return 0


if __name__ == "__main__":
    sys.exit(main())
