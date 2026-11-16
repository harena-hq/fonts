#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Build Harena UI Icons from data/icons/table.json.

One glyph per table row, mapped at every code point of that Segoe glyph. Every outline is an
upstream's, whole: a Fluent icon, or Harena UI J's letters. It is scaled without distortion to fill
the Segoe glyph's ink box on one axis and centred on the other, so nothing here is drawn or traced.

Usage: python scripts/build_icons.py [output.ttf]
"""
import json
import re
import sys
from pathlib import Path

import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont, newTable

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "sources/fluent/package/icons"
OUTPUT = ROOT / "dist/HarenaUIIcons-Regular.ttf"

VERSION = "0.5.2"
VENDOR = "HRNA"
TIMESTAMP = 3_850_000_000  # fixed, so that two builds are the same bytes
UPM = 2048
FAMILY = "Harena UI Icons"
COPYRIGHT = ("Copyright 2020 Microsoft Corporation (https://github.com/microsoft/fluentui-system-icons), "
             "icon outlines under the MIT License\n"
             "Copyright 2020 The Open Sans Project Authors (https://github.com/googlefonts/opensans)\n"
             "Copyright (c) 2021, Kil Hyung-jin (https://github.com/orioncactus/pretendard), "
             "with Reserved Font Name Pretendard JP\n"
             "Copyright 2026 Jeeyong Um")
LICENSE = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
           "This license is available with a FAQ at: https://openfontlicense.org")
PLACEHOLDER = "square_hint_16_regular"
BADGES = {"add": "add_circle", "dismiss": "dismiss_circle", "checkmark": "checkmark_circle", "warning": "warning",
          "error": "error_circle", "lock": "lock_closed", "prohibited": "prohibited", "clock": "clock", "heart": "heart",
          "charge": "flash"}
# A row may name any other stem as its badge.
# The one composition recipe, in a 20-unit square: a filled badge at the bottom right, the base
# knocked out around it.
BADGE_SIZE = 11
BADGE_GAP = 1
MAX_LOSS = 0.40
TEXT_FACES = {"light": "Light", "regular": "Regular", "bold": "Bold"}
SYMBOLS = ROOT / "sources/pjp/public/variable/PretendardJPVariable.ttf"
SYMBOL_WEIGHT = {"light": 300, "regular": 400, "bold": 700}
MAX_ERR = 1.0  # font units, cubic to quadratic


def svg(icon):
    """An icon's outline, y up, with its viewBox's side."""
    text = (ICONS / f"{icon}.svg").read_text()
    size = int(re.search(r'viewBox="0 0 (\d+) \d+"', text)[1])
    pen = RecordingPen()
    flip = TransformPen(pen, Transform(1, 0, 0, -1, 0, size))
    for d in re.findall(r'<path[^>]*\sd="([^"]+)"', text):
        subpaths(d).replay(flip)
    return pen, size


def subpaths(d):
    """Parse one path. SVG lets a command follow `z` with no moveto, from the subpath's start, which
    fontTools' parser refuses, so each subpath is parsed from the start of the one before."""
    out, start = RecordingPen(), None
    for piece in re.findall(r"[^zZ]+[zZ]?", d):
        if not piece.strip():
            continue
        part = RecordingPen()
        parse_path(f"M{start[0]} {start[1]}{piece}" if start else piece, part)
        ops = part.value
        if start and ops[1][0] == "endPath":  # the moveto added above, where the piece brought its own
            ops = ops[2:]
        start = [op for op in ops if op[0] == "moveTo"][-1][1][0]  # z closes the piece's last subpath
        out.value.extend(("closePath", ()) if op[0] == "endPath" else op for op in ops)  # a fill closes them all
    return out


def scaled(recording, k, dx=0, dy=0):
    pen = RecordingPen()
    recording.replay(TransformPen(pen, Transform(k, 0, 0, k, dx, dy)))
    return pen


# Signal strength as Segoe draws its ladder: four rising bars on a 20-unit grid, the first `level`
# filled and the rest outlined. Fluent's own bars leave the empty ones out.
BAR_X, BAR_WIDTH, BAR_HEIGHTS, BAR_LINE = (2, 6.5, 11, 15.5), 3, (5, 9, 13, 17), 1


def bars(level):
    pen = RecordingPen()
    def rect(x0, y0, x1, y1, clockwise):
        corners = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
        pen.moveTo(corners[0])
        for corner in (corners[1:] if clockwise else corners[:0:-1]):
            pen.lineTo(corner)
        pen.closePath()
    for i, (x, h) in enumerate(zip(BAR_X, BAR_HEIGHTS)):
        rect(x, 2, x + BAR_WIDTH, 2 + h, True)
        if i >= level:
            rect(x + BAR_LINE, 2 + BAR_LINE, x + BAR_WIDTH - BAR_LINE, 2 + h - BAR_LINE, False)
    return pen


def to_path(recording):
    path = pathops.Path()
    recording.replay(path.getPen())
    return path


def circle(cx, cy, r):
    path = pathops.Path()
    pen = path.getPen()
    c = r * 0.5522847498
    pen.moveTo((cx + r, cy))
    pen.curveTo((cx + r, cy + c), (cx + c, cy + r), (cx, cy + r))
    pen.curveTo((cx - c, cy + r), (cx - r, cy + c), (cx - r, cy))
    pen.curveTo((cx - r, cy - c), (cx - c, cy - r), (cx, cy - r))
    pen.curveTo((cx + c, cy - r), (cx + r, cy - c), (cx + r, cy))
    pen.closePath()
    return path


def compose(base, badge):
    """base + badge by the recipe, and the share of the base's ink it removed."""
    outline, size = svg(base)
    grid = to_path(scaled(outline, 20 / size))
    grid.simplify(fix_winding=True)
    mark, side = svg(f"{BADGES.get(badge, badge)}_16_filled")
    left = 20 - BADGE_SIZE
    placed = scaled(mark, BADGE_SIZE / side, left, 0)
    hole = circle(left + BADGE_SIZE / 2, BADGE_SIZE / 2, BADGE_SIZE / 2 + BADGE_GAP)
    kept = pathops.op(grid, hole, pathops.PathOp.DIFFERENCE)
    loss = 1 - abs(kept.area) / abs(grid.area)
    both = pathops.op(kept, to_path(placed), pathops.PathOp.UNION)
    pen = RecordingPen()
    both.draw(pen)
    return pen, loss


def text_outline(row, faces, symbols):
    """The row's characters in a Harena UI J face, or in Pretendard JP's symbols where it has none."""
    face = faces[row["weight"]]
    upm = face["head"].unitsPerEm
    pen, x = RecordingPen(), 0
    for ch in row["text"]:
        if ord(ch) in face.getBestCmap():
            source, glyphs, k = face, face.getGlyphSet(), UPM / upm
        else:
            source = symbols
            glyphs = symbols.getGlyphSet(location={"wght": SYMBOL_WEIGHT[row["weight"]]})
            k = UPM / symbols["head"].unitsPerEm
        name = source.getBestCmap()[ord(ch)]
        rec = DecomposingRecordingPen(glyphs)
        glyphs[name].draw(rec)
        rec.replay(TransformPen(pen, Transform(k, 0, 0, k, x, 0)))
        x += glyphs[name].width * k
    return pen


def bounds(recording):
    pen = BoundsPen(None)
    recording.replay(pen)
    return pen.bounds


def fit(recording, box):
    """Uniformly into box: it fills one axis and is centred on the other."""
    x0, x1, y0, y1 = box
    a, c, b, d = bounds(recording)
    k = min((x1 - x0) / (b - a) if b > a else float("inf"), (y1 - y0) / (d - c) if d > c else float("inf"))
    return scaled(recording, k, (x0 + x1) / 2 - k * (a + b) / 2, (y0 + y1) / 2 - k * (c + d) / 2)


def holes(icon):
    """The subpaths after a filled circle's first, the symbol it knocks out."""
    outline, size = svg(icon)
    parts, current = [], []
    for op in outline.value:
        current.append(op)
        if op[0] in ("closePath", "endPath"):
            parts.append(current)
            current = []
    pen = RecordingPen()
    pen.value = [op for part in parts[1:] for op in part]
    return pen, size


def glyph_of(recording, reverse=True):
    """Fluent's outlines come through a y flip and want reversing; TrueType sources already wind right."""
    pen = TTGlyphPen(None)
    recording.replay(Cu2QuPen(pen, MAX_ERR, reverse_direction=reverse))
    return pen.glyph()


def build(out=OUTPUT):
    points = json.loads((ROOT / "data/v0_5/segoe-icons.json").read_text())["points"]
    advance = {p[0]: p[2] for p in points}
    box = {p[0]: p[3] for p in points}
    rows = json.loads((ROOT / "data/icons/table.json").read_text())["rows"]
    faces = {k: TTFont(ROOT / f"dist/HarenaUIJ-Text{v}.ttf") for k, v in TEXT_FACES.items()}
    symbols = TTFont(SYMBOLS)
    by_point = {row["points"][0]: row for row in rows}

    def raw(row):
        kind = row["kind"]
        if kind == "fluent":
            outline = svg(row["icon"])[0]
            if row.get("rotate"):  # a quarter turn: Segoe draws these upright, Fluent on its side
                pen = RecordingPen()
                outline.replay(TransformPen(pen, Transform(0, 1, -1, 0, 0, 0)))
                return pen
            return outline
        if kind == "compose":
            return compose(row["icon"], row["badge"])[0]
        if kind == "text":
            return text_outline(row, faces, symbols)
        if kind == "mirror":
            pen = RecordingPen()
            raw(by_point[row["of"]]).replay(TransformPen(pen, Transform(-1, 0, 0, 1, 0, 0)))
            return pen
        if kind == "bars":
            return bars(row["level"])
        if kind == "none":
            return svg(PLACEHOLDER)[0]
        raise ValueError(f"unknown kind {kind}")

    order, glyphs, metrics, cmap = [".notdef"], {".notdef": TTGlyphPen(None).glyph()}, {".notdef": (UPM, 0)}, {}
    for row in rows:
        first = row["points"][0]
        name = f"uni{first}"
        if row["kind"] == "blank":
            glyph = TTGlyphPen(None).glyph()
        elif row["kind"] == "holes":
            outline, size = holes(row["icon"])
            whole = svg(row["icon"])[0]
            a, c, b, d = bounds(whole)
            x0, x1, y0, y1 = box[row["with"]]
            k = min((x1 - x0) / (b - a), (y1 - y0) / (d - c))
            glyph = glyph_of(scaled(outline, k, (x0 + x1) / 2 - k * (a + b) / 2, (y0 + y1) / 2 - k * (c + d) / 2))
        else:
            glyph = glyph_of(fit(raw(row), box[first]), reverse=row["kind"] not in ("text", "bars"))
        order.append(name)
        glyphs[name] = glyph
        metrics[name] = (advance[first], 0)
        for p in row["points"]:
            cmap[int(p, 16)] = name

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    glyf = fb.font["glyf"]
    fb.setupHorizontalMetrics({n: (metrics[n][0], glyf[n].xMin if glyf[n].numberOfContours else 0) for n in order})
    fb.setupHorizontalHeader(ascent=UPM, descent=0, lineGap=0)
    fb.setupNameTable({
        "copyright": COPYRIGHT, "familyName": FAMILY, "styleName": "Regular",
        "uniqueFontIdentifier": f"{VERSION};{VENDOR};HarenaUIIcons-Regular", "fullName": FAMILY,
        "version": f"Version {VERSION}", "psName": "HarenaUIIcons-Regular",
        "licenseDescription": LICENSE, "licenseInfoURL": "https://openfontlicense.org",
    })
    fb.setupOS2(version=4, sTypoAscender=UPM, sTypoDescender=0, sTypoLineGap=0, usWinAscent=UPM, usWinDescent=0,
                achVendID=VENDOR, fsSelection=0x40 | 0x80, usWeightClass=400)
    fb.setupPost(keepGlyphNames=False)
    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x000A}
    fb.font["gasp"] = gasp
    head = fb.font["head"]
    head.created = head.modified = TIMESTAMP
    head.fontRevision = float(VERSION.rsplit(".", 1)[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    fb.font.save(out)
    return out


def main():
    print(build(Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT))


if __name__ == "__main__":
    main()
