#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Gate for Harena UI Icons: Segoe Fluent Icons' map, advances, metrics and ink boxes, and every
outline reproduced from data/icons/table.json.

Imported by scripts/verify.py, or run alone. Any failure exits non-zero.

Usage: python scripts/verify_icons.py
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

import build_icons
from build_icons import ICONS, MAX_LOSS, OUTPUT, PLACEHOLDER, ROOT, compose

EXPECTED_NONE = 7  # PLAN.md lists them
# Excluded from I7: these sit where Fluent put them in the circle, so they align with it, not Segoe's box.
HOLES_WITH = "F136"
HOLES = {"error_circle_16_filled", "dismiss_circle_16_filled", "checkmark_circle_16_filled", "info_16_filled"}
KINDS = {"blank", "fluent", "compose", "mirror", "text", "holes", "none"}
FORBIDDEN = {"GSUB", "GPOS", "GDEF", "kern", "fpgm", "prep", "cvt ", "COLR", "CPAL", "SVG ", "CBDT", "sbix"}
INK_TOLERANCE = 2  # font units: outlines round to whole units


def checks(font_path=OUTPUT):
    font = TTFont(font_path)
    measured = json.loads((ROOT / "data/v0_5/segoe-icons.json").read_text())
    points = {p[0]: p for p in measured["points"]}
    rows = json.loads((ROOT / "data/icons/table.json").read_text())["rows"]
    cmap = {format(k, "04X"): v for k, v in font.getBestCmap().items()}
    glyf, hmtx = font["glyf"], font["hmtx"]
    glyphset = font.getGlyphSet()

    yield "I1 cmap is Segoe's", set(cmap) == set(points), f"{len(cmap)} of {len(points)}"

    groups = {}
    for p, group, _, _ in measured["points"]:
        groups.setdefault(group, set()).add(p)
    seen = [frozenset(r["points"]) for r in rows]
    yield "I2 one row per glyph", sorted(map(sorted, seen)) == sorted(map(sorted, groups.values())), f"{len(rows)} rows"
    apart = [r["points"][0] for r in rows if len({cmap.get(p) for p in r["points"]}) != 1]
    yield "I2 a row's points share a glyph", not apart, str(apart[:6])
    merged = len({cmap[r["points"][0]] for r in rows}) != len(rows)
    yield "I2 no two rows share a glyph", not merged, ""

    off = [p for p, row in points.items() if p in cmap and hmtx[cmap[p]][0] != row[2]]
    yield "I3 advances are Segoe's", not off, str(off[:6])

    head, hhea, os2 = font["head"], font["hhea"], font["OS/2"]
    metrics = (head.unitsPerEm, hhea.ascent, hhea.descent, hhea.lineGap, os2.sTypoAscender, os2.sTypoDescender,
               os2.sTypoLineGap, os2.usWinAscent, os2.usWinDescent)
    want = (measured["upm"], *measured["hhea"], *measured["typo"], *measured["win"])
    yield "I4 metrics are Segoe's", metrics == want, str(metrics)
    extra = sorted(FORBIDDEN & set(font.keys()))
    yield "I4 no layout, hinting or colour table", not extra, str(extra)

    wrongly_blank = [r["points"][0] for r in rows if (r["kind"] == "blank") != (points[r["points"][0]][3] is None)]
    yield "I5 blank exactly where Segoe has no ink", not wrongly_blank, str(wrongly_blank[:6])
    stray = [r["points"][0] for r in rows if r["kind"] == "holes" and (r.get("with") != HOLES_WITH or r["icon"] not in HOLES)]
    yield "I5 cut-out rows are the four, over their circle", not stray and sum(r["kind"] == "holes" for r in rows) == len(HOLES), str(stray)
    turned = [r["points"][0] for r in rows if r.get("rotate") not in (None, 90)]
    yield "I5 a turned row turns a quarter", not turned, str(turned)
    bad_kind = [r["points"][0] for r in rows if r["kind"] not in KINDS]
    yield "I5 known kinds", not bad_kind, str(bad_kind[:6])
    missing = [r["icon"] for r in rows if "icon" in r and not (ICONS / f"{r['icon']}.svg").exists()]
    missing += [PLACEHOLDER] if not (ICONS / f"{PLACEHOLDER}.svg").exists() else []
    yield "I5 every Fluent name is in the pinned package", not missing, str(missing[:6])
    nones = sum(r["kind"] == "none" for r in rows)
    yield "I5 none is the recorded count", nones == EXPECTED_NONE, f"{nones} of {EXPECTED_NONE}"
    over = [(r["points"][0], round(compose(r["icon"], r["badge"])[1], 3)) for r in rows if r["kind"] == "compose"]
    over = [o for o in over if o[1] >= MAX_LOSS]
    yield "I6 no composition removes 40% of its base", not over, str(over[:6])

    def ink(name):
        pen = BoundsPen(glyphset)
        glyphset[name].draw(pen)
        return pen.bounds

    outside, loose, uncentred, blank_ink, empty = [], [], [], [], []
    t = INK_TOLERANCE
    for r in rows:
        first = r["points"][0]
        name, box = cmap[first], points[first][3]
        b = ink(name) if glyf[name].numberOfContours else None
        if r["kind"] == "blank":
            if b:
                blank_ink.append(first)
            continue
        if not b:
            empty.append(first)
            continue
        if r["kind"] == "holes":  # placed where Fluent put them inside the circle row `with`
            limit = points[r["with"]][3]
            if not (limit[0] - t <= b[0] and b[2] <= limit[1] + t and limit[2] - t <= b[1] and b[3] <= limit[3] + t):
                outside.append(first)
            continue
        x0, x1, y0, y1 = box
        if b[0] < x0 - t or b[2] > x1 + t or b[1] < y0 - t or b[3] > y1 + t:
            outside.append((first, b, box))
        fills_x = b[2] - b[0] >= x1 - x0 - 2 * t
        fills_y = b[3] - b[1] >= y1 - y0 - 2 * t
        if not (fills_x or fills_y):
            loose.append(first)
        if abs((b[0] + b[2]) / 2 - (x0 + x1) / 2) > t or abs((b[1] + b[3]) / 2 - (y0 + y1) / 2) > t:
            uncentred.append(first)
    yield "I7 ink lies in Segoe's box", not outside, str(outside[:3])
    yield "I7 ink fills it on one axis", not loose, str(loose[:6])
    yield "I7 ink is centred in it", not uncentred, str(uncentred[:6])
    yield "I7 only blank rows have no ink", not (blank_ink or empty), str((blank_ink + empty)[:6])

    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = Path(tmp) / "a.ttf"
        again = Path(tmp) / "b.ttf"
        build_icons.build(rebuilt)
        build_icons.build(again)
        yield "I8 two builds are the same bytes", rebuilt.read_bytes() == again.read_bytes(), ""
        yield "I8 every outline is reproduced from its row", rebuilt.read_bytes() == Path(font_path).read_bytes(), ""

    sums = (ROOT / "SHA256SUMS-Icons").read_text().split()
    digest = hashlib.sha256(Path(font_path).read_bytes()).hexdigest()
    yield "I9 SHA256SUMS-Icons matches", sums[:1] == [digest], ""

    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).returncode

    tracked = ("SHA256SUMS-Icons", "data/icons/table.json", "data/v0_5/segoe-icons.json")
    clean = all(git("cat-file", "-e", f"HEAD:{t}") == 0 for t in tracked) and git("diff", "--quiet", "HEAD", "--", *tracked) == 0
    yield "I9 what it checks is committed", clean, ""


def main():
    failed = 0
    for name, ok, detail in checks():
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))
        failed += not ok
    print("gate:", "FAIL" if failed else "PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
