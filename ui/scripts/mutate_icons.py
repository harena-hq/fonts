#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Prove the icon gate catches what it claims to: each mutation must fail its own check, not just the
byte comparison every changed font fails.

Usage: python scripts/mutate_icons.py
"""
import json
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont, newTable

import verify_icons
from build_icons import OUTPUT, ROOT

TABLE = ROOT / "data/icons/table.json"


def advance(font):
    name = font.getBestCmap()[0xE700]
    font["hmtx"][name] = (font["hmtx"][name][0] + 1, font["hmtx"][name][1])


def metric(font):
    font["hhea"].ascent += 1


def typo(font):
    font["OS/2"].sTypoLineGap = 92


def drop_point(font):
    for table in font["cmap"].tables:
        table.cmap.pop(0xE700, None)


def split_row(font):
    for table in font["cmap"].tables:
        if 0xE001 in table.cmap:
            table.cmap[0xE008] = table.cmap[0xE700]


def layout_table(font):
    font["kern"] = newTable("kern")
    font["kern"].version = 0
    font["kern"].kernTables = []


def glyph_program(font):
    font["glyf"][font.getBestCmap()[0xE700]].program.fromBytecode([176, 0, 33])


def outline_moves(font):
    name = font.getBestCmap()[0xE700]
    glyph = font["glyf"][name]
    glyph.coordinates.translate((400, 0))
    glyph.recalcBounds(font["glyf"])
    # A renderer places a glyph by its left side bearing, as the gate's reader does, not by its xMin.
    font["hmtx"][name] = (font["hmtx"][name][0], font["hmtx"][name][1] + 400)


def outline_shrinks(font):
    glyph = font["glyf"][font.getBestCmap()[0xE700]]
    glyph.coordinates.scale((0.5, 0.5))
    glyph.recalcBounds(font["glyf"])


FONT_MUTATIONS = [
    (glyph_program, "I4 no glyph carries instructions"),
    (advance, "I3 advances are Segoe's"), (metric, "I4 metrics are Segoe's"), (typo, "I4 metrics are Segoe's"),
    (drop_point, "I1 cmap is Segoe's"), (split_row, "I2 a row's points share a glyph"),
    (layout_table, "I4 no layout, hinting or colour table"), (outline_moves, "I7 ink lies in Segoe's box"),
    (outline_shrinks, "I7 ink fills it on one axis"),
]


def table_icon(doc):
    next(r for r in doc["rows"] if r["kind"] == "fluent")["icon"] = "no_such_icon_16_regular"


def table_none(doc):
    next(r for r in doc["rows"] if r["kind"] == "fluent").update(kind="none")


def table_row(doc):
    doc["rows"].pop(10)


def table_compose(doc):
    next(r for r in doc["rows"] if r["kind"] == "compose").update(icon="wifi_warning_20_regular", badge="lock")


def table_blank(doc):
    next(r for r in doc["rows"] if r["kind"] == "fluent").update(kind="blank")


def table_holes(doc):
    next(r for r in doc["rows"] if r["kind"] == "holes")["with"] = "E700"


def table_text(doc):
    next(r for r in doc["rows"] if r["kind"] == "text")["text"] = "Z"


def table_bars(doc):
    next(r for r in doc["rows"] if r["kind"] == "bars")["level"] += 1


def table_mirror(doc):
    row = next(r for r in doc["rows"] if r["kind"] == "mirror")
    row["of"] = "E700"


def table_turn(doc):
    next(r for r in doc["rows"] if r.get("rotate"))["rotate"] = 45


TABLE_MUTATIONS = [
    (table_icon, "I5 every Fluent name is in the pinned package"), (table_none, "I5 none is the recorded count"),
    (table_row, "I2 one row per glyph"), (table_blank, "I5 blank exactly where Segoe has no ink"),
    (table_holes, "I5 cut-out rows are the four, over their circle"), (table_turn, "I5 a turned row turns a quarter"),
    (table_text, "I8 every outline is reproduced from its row"), (table_mirror, "I8 every outline is reproduced from its row"),
    (table_bars, "I8 every outline is reproduced from its row"),
    (table_compose, "I6 no composition removes 40% of its base"),
]


def failing(path=None):
    """The checks that fail until one raises: a broken font may stop the later ones, and that stops the gate too."""
    names = set()
    try:
        for name, ok, _ in verify_icons.checks(path or OUTPUT):
            if not ok:
                names.add(name)
    except (OSError, KeyError, ValueError, TypeError):
        pass
    return names


def main():
    missed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for mutate, expected in FONT_MUTATIONS:
            font = TTFont(OUTPUT)
            mutate(font)
            path = Path(tmp) / "mutated.ttf"
            font.save(path)
            got = failing(path)
            print("caught" if expected in got else "MISSED", mutate.__name__, "->", expected)
            missed += expected not in got
    original = TABLE.read_text()
    try:
        for mutate, expected in TABLE_MUTATIONS:
            doc = json.loads(original)
            mutate(doc)
            TABLE.write_text(json.dumps(doc))
            names = failing()
            print("caught" if expected in names else "MISSED", mutate.__name__, "->", expected)
            missed += expected not in names
    finally:
        TABLE.write_text(original)
    print("mutations:", "FAIL" if missed else "PASS")
    sys.exit(1 if missed else 0)


if __name__ == "__main__":
    main()
