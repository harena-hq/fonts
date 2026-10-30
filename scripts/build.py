# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Build Harena UI's fifteen faces (v0.2) from Open Sans and Segoe's measured geometry.

Each face stands for one face Edge draws from Segoe UI Variable: Small, Text or
Display at Light, Semilight, Regular, Semibold or Bold (docs/adr/0004). Its
shapes are Open Sans', instanced at one point of its `wght` x `wdth` space and
otherwise unchanged except for a horizontal shift per glyph. Its geometry is
that Segoe face's, as Edge on Windows draws it (docs/adr/0001), from
data/v0_2/segoe/: advances, pair kerning, tabular digits and vertical metrics.
The target set is v0.1's (data/v0_1/segoe-ui-variable.json).

Writes dist/HarenaUI-<Size><Weight>.ttf and SHA256SUMS; data/v0_2/build.json
(each face's chosen point, any clamp to Open Sans' axes, and the glyph copies,
which the gate checks); and build/v0_2-report.json (diagnostics).

Usage: python scripts/build.py
"""
import hashlib
import json
import math
import os
import statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from fontTools import subset
from fontTools.misc.timeTools import timestampSinceEpoch
from fontTools.otlLib.builder import buildLookup, buildPairPosGlyphs, buildValue
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
OPEN_SANS = ROOT / "sources/opensans/OpenSans[wdth,wght].ttf"
TARGET = ROOT / "data/v0_1/segoe-ui-variable.json"
SEGOE = ROOT / "data/v0_2/segoe"
DIST = ROOT / "dist"

SIZES = ("Small", "Text", "Display")
WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
FACES = [(size, w) for size in SIZES for w in WEIGHTS]

VERSION = "0.2.0"
VENDOR = "HRNA"
# SOURCE_DATE_EPOCH overrides it, following the reproducible-builds convention.
SOURCE_DATE = int(os.environ.get("SOURCE_DATE_EPOCH", "1793318400"))  # 2026-10-30

# Segoe UI Variable's vertical metrics, in units of its 2048 em, which is also Open Sans'.
UPM = 2048
HHEA = {"ascent": 2210, "descent": -514, "lineGap": 0}
TYPO = {"sTypoAscender": 1491, "sTypoDescender": -431, "sTypoLineGap": 269}
WIN = {"usWinAscent": 2210, "usWinDescent": 514}

COPYRIGHT = ("Copyright 2020 The Open Sans Project Authors (https://github.com/googlefonts/opensans)\n"
             "Copyright 2026 Jeeyong Um")
LICENSE = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
           "This license is available with a FAQ at: https://openfontlicense.org")


def face_name(size, w):
    return f"{size}-{WEIGHTS[w]}"


def face_path(size, w):
    return DIST / f"HarenaUI-{size}{WEIGHTS[w]}.ttf"


def names(size, w):
    """Segoe UI Variable's three families, weight as the style: `Harena UI Text`
    with Light ... Bold. Regular and Bold are the legacy family's own styles; the
    other weights get a legacy family of their own, as static Segoe UI's do."""
    family, style = f"Harena UI {size}", WEIGHTS[w]
    ribbi = style in ("Regular", "Bold")
    ps = f"HarenaUI{size}-{style}"
    return {0: COPYRIGHT,
            1: family if ribbi else f"{family} {style}",
            2: style if ribbi else "Regular",
            3: f"{VERSION};{VENDOR};{ps}",
            4: f"{family} {style}",
            5: f"Version {VERSION}",
            6: ps,
            13: LICENSE,
            14: "https://openfontlicense.org",
            16: family,
            17: style}

PX = UPM / 1000  # measured px at a 1000 px font size -> font units


def units(px):
    return round(px * PX)


def ink_x(font, glyph):
    """Tight horizontal bounds of the drawn outline, or None for an empty glyph."""
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    gs[glyph].draw(pen)
    return None if pen.bounds is None else (pen.bounds[0], pen.bounds[2])


def segoe(size, w):
    target = json.loads(TARGET.read_text())["target"]
    return target, json.loads((SEGOE / f"{face_name(size, w)}.json").read_text())


# --- choosing the point ------------------------------------------------------


def working_source(target):
    """Open Sans subset to the target set and `l`: instancing it is fast."""
    f = TTFont(OPEN_SANS)
    opts = subset.Options()
    opts.layout_features = []
    opts.notdef_outline = True
    s = subset.Subsetter(opts)
    s.populate(unicodes=list(target) + [ord("l")])
    s.subset(f)
    return f


def instance(source, wght, wdth):
    return instantiateVariableFont(TTFont(source) if isinstance(source, Path) else _copy(source),
                                   {"wght": wght, "wdth": wdth}, updateFontNames=False)


def _copy(font):
    import io
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    return TTFont(buf)


def stem(font):
    lo, hi = ink_x(font, font.getBestCmap()[ord("l")])
    return (hi - lo) / PX  # px at 1000


def axis(src, tag):
    a = next(a for a in src["fvar"].axes if a.axisTag == tag)
    return a.minValue, a.maxValue


def wght_for_stem(src, wdth, target_px):
    """The wght whose `l` stem is target_px, or the end of Open Sans' wght axis
    nearest to it when the stem is outside the axis' range. Stem width is
    near-linear in wght; secant steps continue until it is within 0.01 px."""
    lo, hi = axis(src, "wght")
    if target_px <= stem(instance(src, lo, wdth)):
        return lo
    if target_px >= stem(instance(src, hi, wdth)):
        return hi
    a, b = 380.0, 440.0
    sa, sb = stem(instance(src, a, wdth)), stem(instance(src, b, wdth))
    for _ in range(12):
        if sb == sa or abs(sb - target_px) < 0.01:
            break
        c = min(max(a + (b - a) * (target_px - sa) / (sb - sa), lo), hi)
        sc = stem(instance(src, c, wdth))
        a, sa, b, sb = b, sb, c, sc
    return b


def ink_ratio(src, wght, wdth, target, seg):
    f = instance(src, wght, wdth)
    cmap = f.getBestCmap()
    rs = []
    for cp in target:
        row = seg["ink"].get(str(cp))
        b = ink_x(f, cmap[cp])
        if row and b and b[1] - b[0] > 0:
            rs.append((row[1] - row[0]) / ((b[1] - b[0]) / PX))
    return st.median(rs)


def choose_point(target, seg):
    """wdth where Open Sans' median ink width over the target set equals Segoe's,
    with wght at each wdth set so the `l` stem equals Segoe's. Either may stop at
    the end of Open Sans' axis; returns the point and the axes that stopped."""
    src = working_source(target)
    target_stem = seg["stems"]["l"]
    lo, hi = axis(src, "wdth")  # the ratio falls as wdth rises
    clamped = []
    if ink_ratio(src, wght_for_stem(src, hi, target_stem), hi, target, seg) > 1:
        wdth = hi
        clamped.append("wdth")
    elif ink_ratio(src, wght_for_stem(src, lo, target_stem), lo, target, seg) < 1:
        wdth = lo
        clamped.append("wdth")
    else:
        for _ in range(12):
            mid = (lo + hi) / 2
            if ink_ratio(src, wght_for_stem(src, mid, target_stem), mid, target, seg) > 1:
                lo = mid
            else:
                hi = mid
        wdth = round((lo + hi) / 2, 1)
    # A compiled outline sits on whole units, so its stem jitters by a unit as wght
    # rises: take the integer within WINDOW of the solution whose compiled stem is
    # nearest, then the one nearest the solution, then the lower.
    w = wght_for_stem(src, wdth, target_stem)
    lo_w, hi_w = axis(src, "wght")
    near = range(max(int(lo_w), math.floor(w) - WINDOW), min(int(hi_w), math.ceil(w) + WINDOW) + 1)
    stems = {c: compiled_stem(c, wdth) for c in near}
    wght = min(near, key=lambda c: (abs(stems[c] - target_stem), abs(c - w), c))
    # Stopped at the axis' end, with Segoe's stem beyond what the axis reaches.
    if (wght == lo_w and stems[wght] > target_stem) or (wght == hi_w and stems[wght] < target_stem):
        clamped.append("wght")
    return wght, wdth, clamped


WINDOW = 15
_L_SOURCE = None


def compiled_stem(wght, wdth):
    """The `l` stem of the compiled Open Sans instance, from a source holding only
    `l`; instancing and compiling a glyph do not depend on the others."""
    global _L_SOURCE
    if _L_SOURCE is None:
        f = TTFont(OPEN_SANS)
        opts = subset.Options()
        opts.layout_features = []
        s = subset.Subsetter(opts)
        s.populate(unicodes=[ord("l")])
        s.subset(f)
        _L_SOURCE = f
    return stem(_copy(instance(_L_SOURCE, wght, wdth)))


# --- the build ---------------------------------------------------------------


def decompose(font):
    """Replace every composite with its outline, so shifting a base glyph cannot
    move the composites that reference it."""
    gs = font.getGlyphSet()
    glyf = font["glyf"]
    drawn = {}
    for name in font.getGlyphOrder():
        if glyf[name].isComposite():
            rec = DecomposingRecordingPen(gs)
            gs[name].draw(rec)
            pen = TTGlyphPen(None)
            rec.replay(pen)
            drawn[name] = pen.glyph()
    for name, g in drawn.items():
        glyf[name] = g


def drop_hinting(font):
    for tag in ("fpgm", "prep", "cvt ", "cvar", "DSIG", "STAT"):
        if tag in font:
            del font[tag]
    glyf = font["glyf"]
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.numberOfContours > 0:
            g.program = Program()
            g.program.fromBytecode(b"")
    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x000A}  # grey-scale and symmetric smoothing at every size
    font["gasp"] = gasp


def set_advance(font, name, adv):
    """Give glyph `name` the advance `adv`. The ink keeps its shape and sits where
    the leftover sidebearing splits in the source's own left:right ratio.
    Returns the horizontal shift applied."""
    glyf, hmtx = font["glyf"], font["hmtx"]
    adv_old, _ = hmtx[name]
    g = glyf[name]
    if g.numberOfContours == 0:
        hmtx[name] = (adv, 0)
        return 0
    xmin, xmax = ink_x(font, name)
    lsb, rsb = xmin, adv_old - xmax
    if lsb >= 0 and rsb >= 0 and lsb + rsb > 0:
        new_lsb = (adv - (xmax - xmin)) * lsb / (lsb + rsb)
    else:
        new_lsb = lsb + (adv - adv_old) / 2
    dx = round(new_lsb - xmin)
    if dx:
        coords = g.coordinates
        for i in range(len(coords)):
            x, y = coords[i]
            coords[i] = (x + dx, y)
    g.recalcBounds(glyf)
    hmtx[name] = (adv, g.xMin)
    return dx


def unshift(font, name, dx, adv):
    """Put a copy of a respaced glyph back where Open Sans had it: move the ink by
    -dx and restore Open Sans' advance, so the copy is placed from the source in
    one step, as the original was. Placing it from the respaced original instead
    differs where a sidebearing is negative, since the split rule then changes."""
    g = font["glyf"][name]
    if dx and g.numberOfContours > 0:
        g.coordinates = type(g.coordinates)([(x - dx, y) for x, y in g.coordinates])
    g.recalcBounds(font["glyf"])
    font["hmtx"][name] = (adv, getattr(g, "xMin", 0))


def respace(font, target, seg):
    """Set each target glyph's advance to Segoe's. Returns the shift per glyph."""
    cmap = font.getBestCmap()
    return {cmap[cp]: set_advance(font, cmap[cp], units(seg["advance"][str(cp)])) for cp in target}


def copy_glyph(font, name, new):
    """Add `new` as an exact copy of `name`: same outline, metrics, GDEF class, and
    the same place in every mark-attachment lookup, so marks attach to the copy as
    they do to the original. The copy is appended last, so adding it at the end of
    a coverage keeps the coverage sorted by glyph ID."""
    import copy
    font["glyf"][new] = copy.deepcopy(font["glyf"][name])
    font["hmtx"][new] = font["hmtx"][name]
    classes = font["GDEF"].table.GlyphClassDef.classDefs
    if name in classes:
        classes[new] = classes[name]
    # glyf's setter appends the new name to its own glyph order, which may be the
    # font's list; rebuild one order from it rather than appending twice.
    order = list(dict.fromkeys(font["glyf"].glyphOrder + [new]))
    font.setGlyphOrder(order)
    font["glyf"].glyphOrder = order
    font["maxp"].numGlyphs = len(order)
    gpos = font["GPOS"].table
    for lookup in gpos.LookupList.Lookup:
        for st_ in lookup.SubTable:
            t = st_.ExtSubTable if lookup.LookupType == 9 else st_
            kind = t.LookupType if lookup.LookupType == 9 else lookup.LookupType
            pairs = {4: [("MarkCoverage", "MarkArray", "MarkRecord"), ("BaseCoverage", "BaseArray", "BaseRecord")],
                     5: [("MarkCoverage", "MarkArray", "MarkRecord"),
                         ("LigatureCoverage", "LigatureArray", "LigatureAttach")],
                     6: [("Mark1Coverage", "Mark1Array", "MarkRecord"),
                         ("Mark2Coverage", "Mark2Array", "Mark2Record")]}.get(kind, [])
            for cov, arr, recs in pairs:
                glyphs = getattr(t, cov).glyphs
                if name in glyphs:
                    rec = copy.deepcopy(getattr(getattr(t, arr), recs)[glyphs.index(name)])
                    glyphs.append(new)
                    getattr(getattr(t, arr), recs).append(rec)
                    count = {"MarkRecord": "MarkCount", "BaseRecord": "BaseCount",
                             "LigatureAttach": "LigatureCount", "Mark2Record": "Mark2Count"}[recs]
                    setattr(getattr(t, arr), count, len(getattr(getattr(t, arr), recs)))


def respace_ligatures(font, target, seg, base_shift, source_adv):
    """A ligature of target characters takes the width Segoe gives the same
    characters: their advances plus the pair kerning between them.

    Open Sans' ligature glyphs are also what U+FB00-FB04 map to, and Segoe gives
    those characters widths of their own. One glyph cannot carry both, so the
    ligature feature is pointed at a copy (`<name>.liga`), and the mapped glyph
    keeps the character's width. Returns the shift per ligature copy, the copies
    made ({copy: original}), the ligatures left alone, and the component code
    points of each respaced ligature glyph."""
    by_name = {v: k for k, v in font.getBestCmap().items()}
    tset = set(target)
    gsub = font["GSUB"].table
    on = {i for r in gsub.FeatureList.FeatureRecord if r.FeatureTag in ("liga", "clig", "rlig")
          for i in r.Feature.LookupListIndex}
    shift, copies, skipped, components = {}, {}, [], {}
    for i in sorted(on):
        lookup = gsub.LookupList.Lookup[i]
        for st_ in lookup.SubTable:
            t = st_.ExtSubTable if lookup.LookupType == 7 else st_
            if (t.LookupType if lookup.LookupType == 7 else lookup.LookupType) != 4:
                raise SystemExit(f"default ligature feature uses lookup type {lookup.LookupType}")
            for first, ligs in t.ligatures.items():
                for lig in ligs:
                    cps = [by_name.get(c) for c in [first] + list(lig.Component)]
                    if None in cps or not set(cps) <= tset:
                        skipped.append(lig.LigGlyph)
                        continue
                    name = lig.LigGlyph
                    if name in shift or f"{name}.liga" in shift:
                        raise SystemExit(f"ligature {name} is reached twice; its shift would be lost")
                    if name in by_name:  # also a mapped character's glyph
                        new = f"{name}.liga"
                        if new not in copies:
                            copy_glyph(font, name, new)
                            copies[new] = name
                            # Its anchors were copied before move_anchors, so they
                            # are Open Sans'; put the outline back with them.
                            unshift(font, new, base_shift.get(name, 0), source_adv[name])
                        lig.LigGlyph = new
                        name = new
                    px = sum(seg["advance"][str(c)] for c in cps)
                    px += sum(seg["kern"].get(f"{a},{b}", 0.0) for a, b in zip(cps, cps[1:]))
                    shift[name] = set_advance(font, name, round(px * PX))
                    components[name] = cps
    return shift, copies, skipped, components


def tabular_digits(font, seg, base_shift, source_adv):
    """Under `tnum`, every digit takes Segoe's tabular advance for it, which is per
    digit (PLAN.md v0.2): `1` always differs from its default, other digits in
    some faces, all ten in Display Light. The default glyph cannot serve both, so
    a digit whose default advance differs from its tabular one gets a copy
    (`one.tnum`), and the `tnum` lookup is pointed at it, both from the default
    glyph and from anything it already mapped to the default glyph. Returns the
    shift per copy and the copies made ({copy: original})."""
    tab = seg["tabular"]
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    gsub = font["GSUB"].table
    lookups = [gsub.LookupList.Lookup[i] for r in gsub.FeatureList.FeatureRecord if r.FeatureTag == "tnum"
               for i in r.Feature.LookupListIndex]
    subtables = []
    for lookup in lookups:
        for st_ in lookup.SubTable:
            t = st_.ExtSubTable if lookup.LookupType == 7 else st_
            if (t.LookupType if lookup.LookupType == 7 else lookup.LookupType) != 1:
                raise SystemExit("tnum uses a lookup type other than single substitution")
            subtables.append(t)
    if not subtables:
        raise SystemExit("the source has no tnum feature")
    shift, copies = {}, {}
    for key, px in sorted(tab.items()):
        name = cmap[int(key)]
        adv = units(px)
        if hmtx[name][0] == adv:
            continue
        new = f"{name}.tnum"
        copy_glyph(font, name, new)
        copies[new] = name
        unshift(font, new, base_shift.get(name, 0), source_adv[name])
        shift[new] = set_advance(font, new, adv)
        for t in subtables:
            for a, b in list(t.mapping.items()):
                if b == name:
                    t.mapping[a] = new
        subtables[0].mapping[name] = new
    return shift, copies


def move_anchors(font, shift):
    """Mark attachment anchors are in their glyph's coordinates; move them with it."""
    gpos = font["GPOS"].table

    def mv(anchor, name):
        if anchor is not None and shift.get(name):
            anchor.XCoordinate += shift[name]

    for lookup in gpos.LookupList.Lookup:
        for st_ in lookup.SubTable:
            t = st_.ExtSubTable if lookup.LookupType == 9 else st_
            kind = t.LookupType if lookup.LookupType == 9 else lookup.LookupType
            if kind == 4:
                for name, rec in zip(t.MarkCoverage.glyphs, t.MarkArray.MarkRecord):
                    mv(rec.MarkAnchor, name)
                for name, rec in zip(t.BaseCoverage.glyphs, t.BaseArray.BaseRecord):
                    for a in rec.BaseAnchor:
                        mv(a, name)
            elif kind == 5:
                for name, rec in zip(t.MarkCoverage.glyphs, t.MarkArray.MarkRecord):
                    mv(rec.MarkAnchor, name)
                for name, attach in zip(t.LigatureCoverage.glyphs, t.LigatureArray.LigatureAttach):
                    for comp in attach.ComponentRecord:
                        for a in comp.LigatureAnchor:
                            mv(a, name)
            elif kind == 6:
                for name, rec in zip(t.Mark1Coverage.glyphs, t.Mark1Array.MarkRecord):
                    mv(rec.MarkAnchor, name)
                for name, rec in zip(t.Mark2Coverage.glyphs, t.Mark2Array.Mark2Record):
                    for a in rec.Mark2Anchor:
                        mv(a, name)
            elif kind in (1, 2, 3, 7, 8):
                raise SystemExit(f"GPOS lookup type {kind} is not handled; the shift would break it")
    gdef = font["GDEF"].table
    if getattr(gdef, "LigCaretList", None):
        raise SystemExit("GDEF ligature carets are not handled; the shift would break them")


def unmark(font, target):
    """A target character that Unicode does not class as a mark is spacing in
    Segoe. Open Sans classes a few spacing accents (U+0384 tonos and its kin) as
    marks, which makes a shaper zero their advance and attach them to the letter
    before. Make those glyphs base glyphs and take them out of mark attachment.
    Returns the code points changed."""
    import unicodedata
    cmap = font.getBestCmap()
    gdef = font["GDEF"].table
    classes = gdef.GlyphClassDef.classDefs
    names = {cmap[cp]: cp for cp in target
             if unicodedata.category(chr(cp))[0] != "M" and classes.get(cmap[cp]) == 3}
    for name in names:
        classes[name] = 1
    sets = getattr(gdef, "MarkGlyphSetsDef", None)
    for cov in (sets.Coverage if sets else []):
        cov.glyphs = [g for g in cov.glyphs if g not in names]
    gpos = font["GPOS"].table
    for lookup in gpos.LookupList.Lookup:
        for st_ in lookup.SubTable:
            t = st_.ExtSubTable if lookup.LookupType == 9 else st_
            kind = t.LookupType if lookup.LookupType == 9 else lookup.LookupType
            if kind in (4, 5):
                keep = [(g, r) for g, r in zip(t.MarkCoverage.glyphs, t.MarkArray.MarkRecord)
                        if g not in names]
                t.MarkCoverage.glyphs = [g for g, _ in keep]
                t.MarkArray.MarkRecord = [r for _, r in keep]
                t.MarkArray.MarkCount = len(keep)
            elif kind == 6:
                keep = [(g, r) for g, r in zip(t.Mark1Coverage.glyphs, t.Mark1Array.MarkRecord)
                        if g not in names]
                t.Mark1Coverage.glyphs = [g for g, _ in keep]
                t.Mark1Array.MarkRecord = [r for _, r in keep]
                t.Mark1Array.MarkCount = len(keep)
                keep2 = [(g, r) for g, r in zip(t.Mark2Coverage.glyphs, t.Mark2Array.Mark2Record)
                         if g not in names]
                t.Mark2Coverage.glyphs = [g for g, _ in keep2]
                t.Mark2Array.Mark2Record = [r for _, r in keep2]
                t.Mark2Array.Mark2Count = len(keep2)
    return sorted(names.values())


def kern_pairs(font, target, seg, ligatures):
    """Segoe's pair kerning, in units chosen so that each kerned pair's width,
    with both advances already rounded, is Segoe's to within half a unit.

    A ligature stands for its components, so a letter before it kerns as before
    its first component, and a letter after it as after its last; the value is
    chosen so the run's width is Segoe's for the same characters."""
    cmap = font.getBestCmap()
    tset = set(target)
    pairs = {}
    hmtx = font["hmtx"]
    for lig, cps in ligatures.items():
        seq = sum(seg["advance"][str(c)] for c in cps)
        seq += sum(seg["kern"].get(f"{a},{b}", 0.0) for a, b in zip(cps, cps[1:]))
        lig_adv = hmtx[lig][0]
        for x in target:
            px = seg["advance"][str(x)]
            for k, key in ((seg["kern"].get(f"{x},{cps[0]}"), (cmap[x], lig)),
                           (seg["kern"].get(f"{cps[-1]},{x}"), (lig, cmap[x]))):
                if k:
                    v = round((px + seq + k) * PX) - units(px) - lig_adv
                    if v:
                        pairs[key] = (buildValue({"XAdvance": v}), None)
    for key, k in seg["kern"].items():
        a, b = map(int, key.split(","))
        if a not in tset or b not in tset:
            continue
        pa, pb = seg["advance"][str(a)], seg["advance"][str(b)]
        v = round((pa + pb + k) * PX) - units(pa) - units(pb)
        if v:
            pairs[(cmap[a], cmap[b])] = (buildValue({"XAdvance": v}), None)
    return pairs


def add_kern(font, pairs):
    gpos = font["GPOS"].table
    glyph_map = font.getReverseGlyphMap()
    lookup = buildLookup(buildPairPosGlyphs(pairs, glyph_map), flags=0x0008)  # IgnoreMarks
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    feature = ot.Feature()
    feature.FeatureParams = None
    feature.LookupListIndex = [len(gpos.LookupList.Lookup) - 1]
    feature.LookupCount = 1
    record = ot.FeatureRecord()
    record.FeatureTag = "kern"
    record.Feature = feature
    records = gpos.FeatureList.FeatureRecord
    records.append(record)
    new = len(records) - 1
    order = sorted(range(len(records)), key=lambda i: (records[i].FeatureTag, i))
    remap = {old: pos for pos, old in enumerate(order)}
    gpos.FeatureList.FeatureRecord = [records[i] for i in order]
    gpos.FeatureList.FeatureCount = len(order)
    for script in gpos.ScriptList.ScriptRecord:
        systems = [script.Script.DefaultLangSys] + [r.LangSys for r in script.Script.LangSysRecord]
        for ls in systems:
            if ls is not None:
                ls.FeatureIndex = sorted(remap[i] for i in ls.FeatureIndex + [new])
                ls.FeatureCount = len(ls.FeatureIndex)


def drop_kern(font):
    """Open Sans carries no kern feature today; refuse if a pinned update adds one."""
    tags = {r.FeatureTag for r in font["GPOS"].table.FeatureList.FeatureRecord}
    if "kern" in tags:
        raise SystemExit("the source has its own kern feature; v0.1 replaces kerning and expects none")


def metrics_and_names(font, size, w):
    hhea, os2 = font["hhea"], font["OS/2"]
    for k, v in HHEA.items():
        setattr(hhea, k, v)
    for k, v in {**TYPO, **WIN}.items():
        setattr(os2, k, v)
    # BOLD on Bold, REGULAR otherwise; never ITALIC (docs/adr/0004); USE_TYPO_METRICS off;
    # WWS off, since "Text" is an optical size, not a weight, width or slope.
    bold = WEIGHTS[w] == "Bold"
    os2.fsSelection = (os2.fsSelection & ~(1 << 7) & ~(1 << 8) & ~0b1100001) | (1 << (5 if bold else 6))
    font["head"].macStyle = 1 if bold else 0
    os2.usWeightClass = w
    os2.usWidthClass = 5
    os2.achVendID = VENDOR
    os2.recalcUnicodeRanges(font)
    os2.recalcCodePageRanges(font)
    os2.recalcAvgCharWidth(font)
    font["post"].italicAngle = 0
    name = font["name"]
    name.names = []
    for nid, value in names(size, w).items():
        name.setName(value, nid, 3, 1, 0x409)
    font["head"].fontRevision = float(VERSION.rsplit(".", 1)[0])
    ts = timestampSinceEpoch(SOURCE_DATE)
    font["head"].created = font["head"].modified = ts
    font.recalcTimestamp = False


def overlaps(font, target, seg):
    """Glyphs whose ink crosses the advance by more than 5 px at 1000 px beyond
    Segoe's own glyph; the gate checks these against data/v0_2/overlaps.json."""
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    out = []
    for cp in target:
        row, b = seg["ink"].get(str(cp)), ink_x(font, cmap[cp])
        if not row or not b:
            continue
        adv = hmtx[cmap[cp]][0] / PX
        ours = min(b[0] / PX, adv - b[1] / PX)
        theirs = min(row[0], seg["advance"][str(cp)] - row[1])
        if ours < min(theirs, 0) - 5:
            out.append(cp)
    return out


def build_face(face):
    size, w = face
    target, seg = segoe(size, w)
    wght, wdth, clamped = choose_point(target, seg)
    # Compile the instance before decomposing, so components are rounded as the
    # static Open Sans instance rounds them, not after being flattened.
    font = _copy(instance(OPEN_SANS, wght, wdth))
    decompose(font)
    drop_hinting(font)
    drop_kern(font)
    source_adv = {g: adv for g, (adv, _) in font["hmtx"].metrics.items()}
    shift = respace(font, target, seg)
    lig_shift, lig_copies, lig_skipped, lig_components = respace_ligatures(font, target, seg, shift,
                                                                           source_adv)
    shift.update(lig_shift)
    tnum_shift, tnum_copies = tabular_digits(font, seg, shift, source_adv)
    shift.update(tnum_shift)
    move_anchors(font, shift)
    unmarked = unmark(font, target)
    pairs = kern_pairs(font, target, seg, lig_components)
    add_kern(font, pairs)
    metrics_and_names(font, size, w)
    out = face_path(size, w)
    font.save(out)
    report = {"wght": wght, "wdth": wdth, "clamped": clamped, "kern_pairs": len(pairs),
              "unmarked": unmarked, "ligatures": sorted(lig_shift), "copies": lig_copies,
              "ligatures_skipped": lig_skipped,
              "overlaps": overlaps(TTFont(out), target, seg)}
    point = {"wght": wght, "wdth": wdth, "clamped": clamped, "copies": {**lig_copies, **tnum_copies}}
    return face_name(size, w), report, point


def build():
    DIST.mkdir(exist_ok=True)
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(build_face, FACES))
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build/v0_2-report.json").write_text(
        json.dumps({name: report for name, report, _ in results}, indent=1) + "\n")
    # What the gate checks rather than trusts; committed, and compared with HEAD.
    (ROOT / "data/v0_2/build.json").write_text(json.dumps(
        {name: point for name, _, point in results}, indent=1, sort_keys=True) + "\n")
    sums = "".join(f"{hashlib.sha256(face_path(*f).read_bytes()).hexdigest()}  "
                   f"{face_path(*f).relative_to(ROOT)}\n" for f in FACES)
    (ROOT / "SHA256SUMS").write_text(sums)
    for name, report, _ in results:
        print(name, json.dumps({k: report[k] for k in ("wght", "wdth", "clamped", "kern_pairs")}),
              "overlaps:", "".join(chr(c) for c in report["overlaps"]))


if __name__ == "__main__":
    build()
