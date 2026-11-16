#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Prove the web gate catches what it claims to: each mutation, made to a copy of dist/web and npm/,
must fail its own check.

Usage: python scripts/mutate_web.py
"""
import re
import shutil
import sys
import tempfile
from pathlib import Path

from fontTools.otlLib.builder import buildLookup, buildPairPosGlyphs, buildValue
from fontTools.ttLib import TTFont

import verify_web
from build import face_path
from build_j import face_path_j
from build_web import WEB, chunks, subset_of, woff2

NPM = verify_web.NPM
J = "j.css"


def chunk(name):
    """J Text Regular's face for one chunk, its range in group 2."""
    return re.compile(r'(@font-face \{\n  font-family: "Harena UI J Text";\n  src: url\("\./fonts/HarenaUIJ-TextRegular-'
                      + re.escape(name) + r'\.woff2"\).*?unicode-range: )([^;]*)(;\n\}\n)', re.S)


def edit(npm, sheet, fn):
    path = npm / sheet
    path.write_text(fn(path.read_text()))


def chunk_range(css, name, fn):
    pattern = chunk(name)
    assert pattern.search(css), name
    return pattern.sub(lambda m: m.group(1) + fn(m.group(2)) + m.group(3), css, count=1)


def narrowed(web, npm):
    edit(npm, J, lambda css: chunk_range(css, "hangul-1", lambda r: r.replace("U+AC00-D7A3", "U+AC01-D7A3")))


def refile(web, name, points):
    """Rewrite J Text Regular's chunk file to hold exactly these code points."""
    data = woff2(subset_of(face_path_j("Text", 400), sorted(points)))
    (web / f"HarenaUIJ-TextRegular-{name}.woff2").write_bytes(data)


def text_chunks():
    return chunks(TTFont(face_path_j("Text", 400), lazy=True).getBestCmap(),
                  TTFont(face_path("Text", 400), lazy=True).getBestCmap())


def split_group(web, npm):
    # あ (tied by kern and halt to the other kana) moves to the symbols file, which is declared after
    # the kana chunk and so checked before it: every code point still draws, from two files.
    parts = text_chunks()
    refile(web, "kana", set(parts["kana"]) - {0x3042})
    refile(web, "symbols", set(parts["symbols"]) | {0x3042})
    edit(npm, J, lambda css: chunk_range(css, "symbols", lambda r: "U+3042, " + r))


def dropped_range(web, npm):
    edit(npm, J, lambda css: chunk("symbols").sub("", css, count=1))


def latin_taken(web, npm):
    edit(npm, J, lambda css: chunk_range(css, "kana", lambda r: "U+41, " + r))


def two_files(web, npm):
    # 가 also in the first rare-syllable chunk, inside its range: two files hold it.
    refile(web, "hangul-2a", set(text_chunks()["hangul-2a"]) | {0xAC00})
    edit(npm, J, lambda css: chunk_range(css, "hangul-2a", lambda r: "U+AC00, " + r))


def byte_flip(web, npm):
    path = web / "HarenaUIJ-TextRegular-kana.woff2"
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))


def empty_index(web, npm):
    (npm / "index.css").write_text("")


def stray_file(web, npm):
    shutil.copy2(web / "HarenaUIJ-TextRegular-kana.woff2", web / "HarenaUIJ-TextRegular-extra.woff2")


def weight_off(web, npm):
    edit(npm, "ui.css", lambda css: css.replace("font-weight: 376 499;", "font-weight: 377 499;", 1))


def override(web, npm):
    edit(npm, J, lambda css: chunk_range(css, "kana", lambda r: r + ";\n  ascent-override: 120%"))


def override_tight(web, npm):
    edit(npm, J, lambda css: chunk_range(css, "kana", lambda r: r + ";Ascent-Override:120%"))


def display(web, npm):
    edit(npm, "icons.css", lambda css: css.replace("font-display: block", "font-display: swap"))


def unkerned(web, npm):
    edit(npm, J, lambda css: css.replace('  font-feature-settings: "kern" 1;\n', "", 1))


def hand_edit(web, npm):
    edit(npm, "ui.css", lambda css: css + "/* edited */\n")


def rewrite(web, name, fn):
    font = TTFont(web / name)
    fn(font)
    font.flavor = "woff2"
    font.save(web / name)


def outline(web, npm):
    def fn(font):
        glyph = font["glyf"][font.getBestCmap()[0xAC00]]
        # A shift alone draws in the same place, as a renderer places a glyph by its side bearing
        glyph.coordinates.scale((0.9, 0.9))
        glyph.recalcBounds(font["glyf"])
    rewrite(web, "HarenaUIJ-TextRegular-hangul-1.woff2", fn)


def hira(ch):
    return 0x3041 <= ord(ch) <= 0x309F


def kata(ch):
    return 0x30A0 <= ord(ch) <= 0x30FF


def mark(ch):
    return 0x3001 <= ord(ch) <= 0x3011


def kana_pair(web, npm):
    # A pair across hiragana and katakana, which a browser shapes as one run: W3 sees it only if its
    # reference shapes them together too.
    add_pair(web, next((a, b) for text in verify_web.strings() for a, b in zip(text, text[1:]) if hira(a) and kata(b)))


def leading_mark(web, npm):
    # A pair from punctuation that opens a string, whose scripts include kana, to the kana after it.
    add_pair(web, next((t[0], t[1]) for t in verify_web.strings() if len(t) > 1 and mark(t[0]) and (hira(t[1]) or kata(t[1]))))


def add_pair(web, chars):
    first, second = chars

    def fn(font):
        cmap = font.getBestCmap()
        gpos = font["GPOS"].table
        pair = buildPairPosGlyphs({(cmap[ord(first)], cmap[ord(second)]): (buildValue({"XAdvance": -100}), None)},
                                  font.getReverseGlyphMap())
        gpos.LookupList.Lookup.append(buildLookup(pair))
        gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
        for record in gpos.FeatureList.FeatureRecord:
            if record.FeatureTag == "kern":
                record.Feature.LookupListIndex.append(gpos.LookupList.LookupCount - 1)
                record.Feature.LookupCount += 1
    rewrite(web, "HarenaUIJ-TextRegular-kana.woff2", fn)


def no_kerning(web, npm):
    rewrite(web, "HarenaUIJ-TextRegular-kana.woff2", lambda font: font.__delitem__("GPOS"))


MUTATIONS = [
    (narrowed, "W1 each file holds its chunk, inside its range"),
    (split_group, "W2 no layout rule ties two files"),
    (dropped_range, "W1 every code point draws from a file, and only the TTF's"),
    (latin_taken, "W1 Latin text reaches no chunk"),
    (two_files, "W1 no code point is in two files"),
    (weight_off, "W4 faces are declared as locked"),
    (override, "W4 faces are declared as locked"),
    (override_tight, "W4 faces are declared as locked"),
    (display, "W4 faces are declared as locked"),
    (unkerned, "W4 faces are declared as locked"),
    (hand_edit, "W5 stylesheets are build_css.py's"),
    (stray_file, "W5 SHA256SUMS-Web lists exactly dist/web"),
    (byte_flip, "W5 SHA256SUMS-Web lists exactly dist/web"),
    (empty_index, "W5 stylesheets are build_css.py's"),
    (outline, "W1 each file's glyphs are its TTF's"),
    (no_kerning, "W3 split runs shape as the whole face"),
    (kana_pair, "W3 split runs shape as the whole face"),
    (leading_mark, "W3 split runs shape as the whole face"),
]


def failing(web, npm):
    names = set()
    try:
        for name, ok, _ in verify_web.checks(web, npm):
            if not ok:
                names.add(name)
    except Exception:  # a damaged file may stop the later checks, and that stops the gate too
        pass
    return names


def main():
    missed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for mutate, expect in MUTATIONS:
            web, npm = Path(tmp) / "web", Path(tmp) / "npm"
            for d in (web, npm):
                shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(WEB, web)
            shutil.copytree(NPM, npm)
            mutate(web, npm)
            caught = expect in failing(web, npm)
            missed += not caught
            print(f"{'CAUGHT' if caught else 'MISSED'} {mutate.__name__}: {expect}", flush=True)
    print("mutations:", "FAIL" if missed else "PASS")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
