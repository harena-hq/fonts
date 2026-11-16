# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Build Harena UI's fifteen faces (v0.3) from Open Sans and Segoe's measured geometry.

Each face stands for one face Edge draws from Segoe UI Variable: Small, Text or
Display at Light, Semilight, Regular, Semibold or Bold (docs/adr/0004). Its
shapes are Open Sans', instanced at one point of its `wght` x `wdth` space and
otherwise unchanged except for a horizontal shift per glyph. Its geometry is
that Segoe face's, as Edge on Windows draws it (docs/adr/0001), from
data/v0_2/segoe/: advances, pair kerning, tabular digits and vertical metrics.
The target set is v0.1's (data/v0_1/segoe-ui-variable.json).

Its features are Segoe's (v0.3, data/v0_3/): Open Sans' features that Segoe
lacks are removed with the glyphs only they reach, except `liga`; `frac` and
`ccmp` produce Segoe's widths, `ccmp` drawing `i` dotless where Segoe's does; and
`dlig` substitutes as Segoe's does, onto Open Sans' presentation forms and a copy
of `r`.

Writes dist/HarenaUI-<Size><Weight>.ttf and SHA256SUMS; data/v0_3/build.json
(each face's chosen point, any clamp to Open Sans' axes, and the glyph copies,
which the gate checks); and build/v0_3-report.json (diagnostics).

Usage: python scripts/build.py
"""
import hashlib
import json
import math
import os
import statistics as st
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from fontTools import subset
from fontTools import unicodedata as fu
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.misc.timeTools import timestampSinceEpoch
from fontTools.otlLib.builder import buildLookup, buildPairPosGlyphs, buildSinglePos, buildValue
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
FEATURES = ROOT / "data/v0_3"
DIST = ROOT / "dist"

SIZES = ("Small", "Text", "Display")
WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
FACES = [(size, w) for size in SIZES for w in WEIGHTS]

VERSION = "0.3.0"
# Features kept from Open Sans: Segoe's GSUB has ccmp, dlig, frac and tnum, and `liga`
# stays from v0.1 (PLAN.md v0.3). Open Sans has no dlig; the build adds Segoe's. GPOS
# gets `kern` from Segoe's numbers.
KEEP_GSUB = ("ccmp", "dlig", "frac", "liga", "tnum")
KEEP_GPOS = ("mark", "mkmk")
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


def segoe_features(size, w):
    """Segoe's feature inventory, and this face's measured feature cases (each with
    its `width`) and base-and-mark matrix (with its `delta`)."""
    inventory = json.loads((FEATURES / "segoe-features.json").read_text())
    shared = json.loads((FEATURES / "cases.json").read_text())
    face = json.loads((FEATURES / "segoe" / f"{face_name(size, w)}.json").read_text())
    cases = [{**c, "width": wd} for c, wd in zip(shared["cases"], face["widths"], strict=True)]
    return inventory, cases, {**shared["marks"], "delta": face["delta"]}


def shaper(font):
    """HarfBuzz over the font as it stands: shape(text, features) -> (glyph names
    with clusters, advance in units)."""
    import io
    import uharfbuzz as hb
    buf = io.BytesIO()
    font.save(buf)
    hb_font = hb.Font(hb.Face(hb.Blob(buf.getvalue())))
    order = font.getGlyphOrder()

    def shape(text, features=None):
        b = hb.Buffer()
        b.add_str(text)
        b.guess_segment_properties()
        hb.shape(hb_font, b, features or {})
        return ([(order[i.codepoint], i.cluster) for i in b.glyph_infos],
                sum(p.x_advance for p in b.glyph_positions))
    return shape


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
    characters: their advances plus the pair kerning between them. The advances
    are the glyph's advance, and the kerning between its components is an
    adjustment in the `kern` feature (internal_kern), so that with kerning
    turned off the ligature is as wide as Segoe's unkerned letters (v0.3).

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


def own_script(base, mark):
    """Whether a combining mark is written after this letter: the mark is of the
    inherited script, or the letter's script is one the mark is used with (Unicode
    Script_Extensions). A Hebrew point after a Latin letter is not text."""
    return fu.script(mark) == "Zinh" or fu.script(base) in fu.script_extension(mark)


def segoe_dotless_marks():
    """The combining marks before which Segoe draws `i` dotless, from v0.3's
    base-and-mark measurements: in every face where `ı` is narrower than `i`,
    `i` and the mark measure as `ı` does."""
    sets = []
    for size, w in FACES:
        seg = segoe(size, w)[1]
        a = seg["advance"]
        if abs(a["105"] - a["305"]) < 0.01:
            continue
        m = segoe_features(size, w)[2]
        sets.append({k for k in m["marks"] if own_script("i", k)
                     and abs(m["delta"][""].get("i" + k, 0.0) - (a["305"] - a["105"])) < 0.05})
    return set.intersection(*sets) if sets else set()


def dotless_letters(font):
    """The characters Open Sans' ccmp draws dotless before a mark above: the inputs
    of the rule extend_dotless extends."""
    cmap, gsub = font.getBestCmap(), font["GSUB"].table
    by_glyph = {}
    for cp, g in cmap.items():
        by_glyph.setdefault(g, set()).add(cp)
    out = set()
    for i in sorted({i for r in gsub.FeatureList.FeatureRecord if r.FeatureTag == "ccmp"
                     for i in r.Feature.LookupListIndex}):
        lookup = gsub.LookupList.Lookup[i]
        for st_ in lookup.SubTable:
            if lookup.LookupType == 6 and st_.Format == 3 and len(st_.LookAheadCoverage) == 1 \
                    and cmap[0x69] in st_.InputCoverage[0].glyphs:
                out |= {cp for g in st_.InputCoverage[0].glyphs for cp in by_glyph.get(g, ())}
    if 0x69 not in out:
        raise SystemExit("Open Sans' ccmp has no dotless rule for i")
    return out


def extend_dotless(font):
    """Open Sans' ccmp makes `i`, `j` and their kin dotless before marks above.
    Segoe's does so before more: the Cyrillic pneumata U+0485 and U+0486
    (segoe_dotless_marks) and the spacing accents (dotless_before), with kerning on
    or off. Those join the lookahead of Open Sans' own rule, which is otherwise
    unchanged, so `liga` and `dlig` then meet a dotless `i` there as Segoe's do.
    Returns the glyphs added."""
    cmap = font.getBestCmap()
    gsub = font["GSUB"].table
    dotless = {cmap[0x69]: cmap[0x131]}
    chars = {ord(k) for k in segoe_dotless_marks()} | dotless_before()
    extra = {cmap[c] for c in chars if c in cmap}
    added = set()
    for i in sorted({i for r in gsub.FeatureList.FeatureRecord if r.FeatureTag == "ccmp"
                     for i in r.Feature.LookupListIndex}):
        lookup = gsub.LookupList.Lookup[i]
        for st_ in lookup.SubTable:
            if lookup.LookupType != 6 or st_.Format != 3 or len(st_.LookAheadCoverage) != 1 \
                    or cmap[0x69] not in st_.InputCoverage[0].glyphs:
                continue
            nested = [gsub.LookupList.Lookup[r.LookupListIndex] for r in st_.SubstLookupRecord]
            if not any(s.mapping.get(cmap[0x69]) == dotless[cmap[0x69]] for n in nested for s in n.SubTable
                       if hasattr(s, "mapping")):
                continue
            new = extra - set(st_.LookAheadCoverage[0].glyphs)
            st_.LookAheadCoverage[0].glyphs = sorted(set(st_.LookAheadCoverage[0].glyphs) | new,
                                                     key=font.getGlyphID)
            added |= new
    return sorted(added)


def _singles(table, tags):
    """Single substitution subtables the features `tags` reach, directly or through
    a chaining context (format 3, which is all Open Sans uses), each once."""
    lookups = table.LookupList.Lookup
    todo = [i for r in table.FeatureList.FeatureRecord if r.FeatureTag in tags
            for i in r.Feature.LookupListIndex]
    seen, out = set(), []
    while todo:
        i = todo.pop()
        if i in seen:
            continue
        seen.add(i)
        lookup = lookups[i]
        for st_ in lookup.SubTable:
            t = st_.ExtSubTable if lookup.LookupType == 7 else st_
            kind = t.LookupType if lookup.LookupType == 7 else lookup.LookupType
            if kind == 1:
                out.append(t)
            elif kind == 6 and t.Format == 3:
                todo.extend(r.LookupListIndex for r in t.SubstLookupRecord)
            elif kind != 4:
                raise SystemExit(f"{tags} use lookup type {kind}, which is not handled")
    return out


def ccmp_widths(font, base_shift, source_adv, seg, marks, cases):
    """`ccmp` keeps Open Sans' substitutions, which put a mark on the right form of a
    letter (a dotless `i` under an accent above). Each output takes the width Segoe
    gives the letter and mark it stands in for (data/v0_3 `marks`, no language):
    Segoe draws `i` + U+0307 as wide as its own `ı`, and Cyrillic `і` + U+0301 as
    wide as `і`. An output that is also a mapped character's glyph and needs
    another width, or that letters needing different widths reach, gets a copy
    (`dotlessi.ccmp`) the substitution points at; one only `ccmp` reaches is
    respaced in place; one no measured sequence reaches is left alone. A ligature
    `ccmp` forms takes the width Segoe gives its characters, measured with a joiner
    between them, which keeps composition from hiding the rule (`A`, ZWJ, ogonek).
    Hebrew `ת` and dagesh, which Open Sans joins into U+FB4A, are as wide as `ת` in
    Segoe; so are `ι` and three marks. One only `ccmp` reaches is respaced in place,
    and a mapped one gets a copy. Returns the shift per glyph changed and the copies made ({copy:
    original})."""
    hmtx, cmap = font["hmtx"], font.getBestCmap()
    mapped = set(cmap.values())
    delta = marks["delta"][""]
    shape = shaper(font)
    subtables = _singles(font["GSUB"].table, ("ccmp",))
    gsub = font["GSUB"].table
    elsewhere = {g for t in _singles(gsub, ("frac", "liga", "tnum")) for g in t.mapping.values()}
    for r in gsub.FeatureList.FeatureRecord:  # and the ligatures those features form
        for i in r.Feature.LookupListIndex if r.FeatureTag in ("frac", "liga", "tnum") else []:
            for st_ in gsub.LookupList.Lookup[i].SubTable:
                for ligs in getattr(st_, "ligatures", {}).values():
                    elsewhere |= {lig.LigGlyph for lig in ligs}
    need = {}  # (input, output) -> widths measured for it
    for t in subtables:
        for a, b in t.mapping.items():
            for cp, g in cmap.items():
                if g != a or str(cp) not in seg["advance"]:
                    continue
                for m in marks["marks"]:
                    text = chr(cp) + m
                    if b in (g_ for g_, _ in shape(text)[0]):
                        need.setdefault((a, b), set()).add(
                            units(seg["advance"][str(cp)] + delta.get(text, 0.0)))
    for key, widths in need.items():
        if len(widths) > 1:
            raise SystemExit(f"ccmp {key} needs widths {sorted(widths)}")
    want = {k: v.pop() for k, v in need.items()}
    by_output = {}
    for (a, b), w in want.items():
        by_output.setdefault(b, set()).add(w)
    shift, copies = {}, {}
    for t in subtables:
        for a, b in list(t.mapping.items()):
            if (a, b) not in want or hmtx[b][0] == want[(a, b)] and len(by_output[b]) == 1:
                continue
            w = want[(a, b)]
            if b in mapped or len(by_output[b]) > 1:
                new = f"{b}.ccmp" if len(by_output[b]) == 1 else f"{b}.ccmp{w}"
                if new not in copies:
                    copy_glyph(font, b, new)
                    copies[new] = b
                    unshift(font, new, base_shift.get(b, 0), source_adv[b])
                    shift[new] = set_advance(font, new, w)
                t.mapping[a] = new
            elif b not in shift:
                if b in base_shift or b in elsewhere:
                    raise SystemExit(f"ccmp output {b} is respaced or reached elsewhere too")
                shift[b] = set_advance(font, b, w)
    by_glyph = {}
    for cp, g in sorted(cmap.items()):
        by_glyph.setdefault(g, cp)
    joined = {c["text"]: c["width"] for c in cases if c["group"] == "joiner" and not c["css"]}
    for i in sorted(_reached(gsub, ("ccmp",))):
        lookup = gsub.LookupList.Lookup[i]
        if lookup.LookupType != 4:
            continue
        for st_ in lookup.SubTable:
            for first, ligs in st_.ligatures.items():
                for lig in ligs:
                    comps = [first] + list(lig.Component)
                    text = "\u200D".join(chr(by_glyph[c]) for c in comps if c in by_glyph)
                    if text not in joined:  # a component Segoe does not map: coverage
                        continue
                    w = units(joined[text])
                    out = lig.LigGlyph
                    if hmtx[out][0] == w:
                        continue
                    if out not in mapped:
                        if out in base_shift or out in elsewhere or out in shift:
                            raise SystemExit(f"ccmp ligature {out} is reached elsewhere too")
                        shift[out] = set_advance(font, out, w)
                        continue
                    new = f"{out}.ccmp"
                    if new in copies:
                        raise SystemExit(f"ccmp ligature {out} needs two widths")
                    copy_glyph(font, out, new)
                    copies[new] = out
                    unshift(font, new, base_shift.get(out, 0), source_adv[out])
                    shift[new] = set_advance(font, new, w)
                    lig.LigGlyph = new
    return shift, copies


def _reached(table, tags):
    """Indices of the lookups the features `tags` use, directly or through a
    chaining context of format 3."""
    todo = [i for r in table.FeatureList.FeatureRecord if r.FeatureTag in tags
            for i in r.Feature.LookupListIndex]
    seen = set()
    while todo:
        i = todo.pop()
        if i not in seen:
            seen.add(i)
            lookup = table.LookupList.Lookup[i]
            todo += [r.LookupListIndex for st_ in lookup.SubTable
                     for r in getattr(st_, "SubstLookupRecord", None) or []]
    return seen


def space_marks(font, marks, base_shift):
    """A combining mark both fonts draw as a spacing glyph (no mark class here, and
    Segoe's measured width after each letter of its script the same) takes Segoe's
    width: the Cyrillic signs U+0488 and U+0489. Returns the shift per glyph."""
    cmap, classes = font.getBestCmap(), font["GDEF"].table.GlyphClassDef.classDefs
    shift = {}
    for m in marks["marks"]:
        g = cmap[ord(m)]
        if classes.get(g) == 3:
            continue
        vals = [marks["delta"][""].get(b + m, 0.0) for b in marks["bases"] if own_script(b, m)]
        if not vals or g in base_shift:
            raise SystemExit(f"spacing mark U+{ord(m):04X} has no measurement, or is respaced already")
        mode = st.mode(round(v, 1) for v in vals)
        if sum(abs(v - mode) < 0.1 for v in vals) < 0.95 * len(vals):
            raise SystemExit(f"spacing mark U+{ord(m):04X} has no one width in Segoe")
        shift[g] = set_advance(font, g, units(st.median(v for v in vals if abs(v - mode) < 0.1)))
    return shift


def frac_widths(font, cases, base_shift):
    """`frac` forms numerators, denominators and the fraction slash, as Segoe's does;
    the slash is U+2044's glyph, which already has Segoe's advance. Each numerator
    takes Segoe's width of `d⁄` under diagonal-fractions less that advance, and each
    denominator Segoe's width of `⁄d` less it, so any kerning Segoe has against the
    slash is in the advance. Nothing else reaches these glyphs. Returns the shift
    per glyph."""
    width = {c["text"]: c["width"] for c in cases
             if c["group"] == "frac" and c["features"] == {"frac": 1}}
    shape = shaper(font)
    cmap = font.getBestCmap()
    mapped = set(cmap.values())
    slash = font["hmtx"][cmap[0x2044]][0]
    shift = {}
    for d in "0123456789":
        for text, at in ((d + "\u2044", 0), ("\u2044" + d, 1)):
            glyphs, _ = shape(text, {"frac": True})
            name = glyphs[at][0]
            if name in shift or name in mapped or name in base_shift:
                raise SystemExit(f"frac reaches {name} twice, a mapped glyph, or a respaced one")
            shift[name] = set_advance(font, name, units(width[text]) - slash)
    return shift


def prune(font):
    """Remove every feature Segoe lacks (KEEP_GSUB, KEEP_GPOS), and every glyph that
    the cmap no longer reaches through the features left. Glyph names, the cmap and
    every other table are kept."""
    opts = subset.Options()
    opts.layout_features = list(KEEP_GSUB + KEEP_GPOS)
    opts.layout_scripts = ["*"]
    opts.glyph_names = opts.notdef_glyph = opts.notdef_outline = True
    opts.name_IDs, opts.name_languages, opts.name_legacy = ["*"], ["*"], True
    opts.hinting = opts.legacy_kern = opts.symbol_cmap = opts.passthrough_tables = True
    opts.drop_tables = []
    opts.prune_unicode_ranges = opts.prune_codepage_ranges = False
    opts.recalc_bounds = opts.recalc_timestamp = opts.canonical_order = False
    cmap = dict(font.getBestCmap())
    before = set(font.getGlyphOrder())
    s = subset.Subsetter(opts)
    s.populate(unicodes=list(cmap))
    s.subset(font)
    if dict(font.getBestCmap()) != cmap:
        raise SystemExit("pruning features changed the cmap")
    for tag, keep in (("GSUB", KEEP_GSUB), ("GPOS", KEEP_GPOS)):
        left = {r.FeatureTag for r in font[tag].table.FeatureList.FeatureRecord}
        if left != set(keep):
            raise SystemExit(f"{tag} kept {sorted(left)}, not {list(keep)}")
    return sorted(before - set(font.getGlyphOrder()))


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


def internal_kern(seg, cps, lig_adv):
    """The adjustment that brings a ligature whose advance is `lig_adv` to Segoe's
    kerned width for its components."""
    px = sum(seg["advance"][str(c)] for c in cps)
    px += sum(seg["kern"].get(f"{a},{b}", 0.0) for a, b in zip(cps, cps[1:]))
    return round(px * PX) - lig_adv


def kern_pairs(font, target, seg, ligatures):
    """Segoe's pair kerning, in units chosen so that each kerned pair's width,
    with both advances already rounded, is Segoe's to within half a unit.

    A ligature stands for its components, so a letter before it kerns as before
    its first component, and a letter after it as after its last; the value is
    chosen so the run's width is Segoe's for the same characters.

    A letter `ccmp` draws dotless before a spacing accent (dotless_letters,
    dotless_before) is not kerned against it: v0.2 measured Segoe's dotless `i`
    there as a pair, which `ccmp` now draws, and with `ccmp` off Segoe sets the
    two unkerned (data/v0_3, the `dotless` cases)."""
    cmap = font.getBestCmap()
    tset = set(target)
    pairs = {}
    unkerned = {(a, b) for a in dotless_letters(font) for b in dotless_before()}
    hmtx = font["hmtx"]
    for lig, cps in ligatures.items():
        seq = sum(seg["advance"][str(c)] for c in cps)
        seq += sum(seg["kern"].get(f"{a},{b}", 0.0) for a, b in zip(cps, cps[1:]))
        lig_adv = round(seq * PX)  # as kerned: its advance plus internal_kern
        for x in target:
            px = seg["advance"][str(x)]
            for k, key in ((seg["kern"].get(f"{x},{cps[0]}"), (cmap[x], lig)),
                           (seg["kern"].get(f"{cps[-1]},{x}"), (lig, cmap[x]))):
                if k and (key[0] != lig or (cps[-1], x) not in unkerned):
                    v = round((px + seq + k) * PX) - units(px) - lig_adv
                    if v:
                        pairs[key] = (buildValue({"XAdvance": v}), None)
    for key, k in seg["kern"].items():
        a, b = map(int, key.split(","))
        if a not in tset or b not in tset or (a, b) in unkerned:
            continue
        pa, pb = seg["advance"][str(a)], seg["advance"][str(b)]
        v = round((pa + pb + k) * PX) - units(pa) - units(pb)
        if v:
            pairs[(cmap[a], cmap[b])] = (buildValue({"XAdvance": v}), None)
    return pairs


def add_kern(font, pairs, singles):
    """`kern`: Segoe's pairs, then the kerning inside each ligature (internal_kern)."""
    gpos = font["GPOS"].table
    glyph_map = font.getReverseGlyphMap()
    first = len(gpos.LookupList.Lookup)
    gpos.LookupList.Lookup.append(
        buildLookup(buildPairPosGlyphs(pairs, glyph_map), flags=0x0008))  # IgnoreMarks
    if singles:
        gpos.LookupList.Lookup.append(buildLookup(
            buildSinglePos({g: buildValue({"XAdvance": v}) for g, v in singles.items()}, glyph_map)))
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    add_feature(gpos, "kern", list(range(first, len(gpos.LookupList.Lookup))))


def add_feature(gpos, tag, indices):
    """A feature `tag` over the lookups `indices`, in every language system."""
    feature = ot.Feature()
    feature.FeatureParams = None
    feature.LookupListIndex = indices
    feature.LookupCount = len(indices)
    record = ot.FeatureRecord()
    record.FeatureTag = tag
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


def _fea_name(glyph):
    return "\\" + glyph


def segoe_dlig(inventory):
    """Segoe's dlig as text (data/v0_3/segoe-features.json): its ligature sequences,
    and its contexts as (characters changed, characters that must follow)."""
    d = inventory["dlig"]
    return (sorted("".join(map(chr, s)) for s in d["sequences"]),
            [({chr(c) for c in x["input"]}, {chr(c) for c in x["lookahead"]}) for x in d["contexts"]])


def first_chars(font, glyph, components):
    """The characters a glyph can begin: those it maps, or a default ligature's
    first component's."""
    by_glyph = {}
    for cp, g in font.getBestCmap().items():
        by_glyph.setdefault(g, set()).add(chr(cp))
    if glyph in components:
        return {chr(components[glyph][0])}
    return by_glyph.get(glyph, set())


def dotless_before():
    """The characters before which Segoe draws `i` dotless (its ccmp), read from
    v0.2's measurements: wherever `ı` is narrower than `i`, `i` before these
    measures as `ı` does, in every such face. `j` and `ȷ` give the same set, and
    v0.3's measurements with kerning off agree for the spacing accents."""
    target = json.loads(TARGET.read_text())
    sets = []
    for size, w in FACES:
        a, k = segoe(size, w)[1]["advance"], segoe(size, w)[1]["kern"]
        if abs(a["105"] - a["305"]) < 0.01:
            continue
        sets.append({x for x in target["kern_pairs_from"]
                     if abs(a["105"] + k.get(f"105,{x}", 0) - a["305"] - k.get(f"305,{x}", 0)) < 0.05})
    return set.intersection(*sets) if sets else set()


def dlig_substitution(font, inventory, cases, components, base_shift, source_adv):
    """Segoe's `dlig`, as Segoe does it (PLAN.md v0.3): a substitution, whose
    glyphs carry their own advances and are kerned by `kern`.

    - Each ligature Segoe forms (`ff`, `ffi`, `ffl`, `ﬀi`) becomes the
      presentation form that decomposes to it (U+FB00, U+FB03, U+FB04), whose
      advance and kerning are already Segoe's: Segoe's dlig ligatures are those
      glyphs (as wide, within 0.012 px, and kerned alike against 99% of the
      measured neighbours). From letters with `liga` off, and from the default
      ligature with it on.
    - Each character of a Segoe context before a character that may follow it
      becomes a copy (`r.dlig`), whose advance is Segoe's from the measurements
      with kerning off.

    Before a spacing accent `ccmp` has already made `i` dotless (extend_dotless),
    so `ffi` does not form there, as in Segoe.

    Adds the GSUB lookups and the copy. Returns the copy's shift and the copies
    made ({copy: original})."""
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    ligatures, contexts = segoe_dlig(inventory)
    forms = {}
    for cp in cmap:
        nfkc = unicodedata.normalize("NFKC", chr(cp))
        if len(nfkc) > 1 and nfkc != chr(cp):
            forms.setdefault(nfkc, cmap[cp])
    lines_lig, lines_single = [], []
    for q in ligatures:
        key = unicodedata.normalize("NFKC", q)
        if key not in forms:
            raise SystemExit(f"Segoe's dlig ligature {q!r} has no presentation form here")
        if not all(ord(ch) in cmap for ch in q):
            raise SystemExit(f"Segoe's dlig ligature {q!r} reads a character this font lacks")
        lines_lig.append((q, forms[key]))
    by_text = {"".join(map(chr, cps)): g for g, cps in components.items()}
    for q, form in lines_lig:
        if unicodedata.normalize("NFKC", q) in by_text and q == unicodedata.normalize("NFKC", q):
            lines_single.append((by_text[q], form))
    width = {(c["text"], json.dumps(c["features"], sort_keys=True)): units(c["width"])
             for c in cases if c["group"] == "dlig"}
    k0 = json.dumps({"dlig": 1, "kern": 0}, sort_keys=True)
    shift, copies, ctx_lines = {}, {}, []
    for first, ahead in contexts:
        for ch in sorted(first):
            if ord(ch) not in cmap:
                raise SystemExit(f"Segoe's dlig context changes {ch!r}, which this font lacks")
            g = cmap[ord(ch)]
            advs = [width[(ch + a, k0)] - hmtx[cmap[ord(a)]][0] for a in sorted(ahead)
                    if ord(a) in cmap and (ch + a, k0) in width]
            if not advs or max(advs) - min(advs) > 1:
                raise SystemExit(f"dlig {ch!r}: advances from kerning off disagree: {sorted(set(advs))}")
            new = f"{g}.dlig"
            copy_glyph(font, g, new)
            copies[new] = g
            unshift(font, new, base_shift.get(g, 0), source_adv[g])
            shift[new] = set_advance(font, new, round(st.median(advs)))
            following = sorted(n for n in font.getGlyphOrder()
                               if first_chars(font, n, components) & ahead and n != new)
            ctx_lines.append((g, new, following))
    fea = []
    if ctx_lines:
        fea.append("lookup dligContext {\n" + "".join(
            f"  sub {_fea_name(g)}' [{' '.join(map(_fea_name, f))}] by {_fea_name(n)};\n"
            for g, n, f in ctx_lines) + "} dligContext;")
    if lines_single:
        fea.append("lookup dligDefault {\n" + "".join(
            f"  sub {_fea_name(a)} by {_fea_name(b)};\n" for a, b in lines_single) + "} dligDefault;")
    fea.append("lookup dligLigatures {\n" + "".join(
        f"  sub {' '.join(_fea_name(cmap[ord(ch)]) for ch in q)} by {_fea_name(f)};\n"
        for q, f in sorted(lines_lig, key=lambda x: (-len(x[0]), x[0]))) + "} dligLigatures;")
    names = [b.split()[1] for b in fea]
    fea_text = "\n".join(fea) + "\nfeature dlig {\n" + "".join(f"  lookup {n};\n" for n in names) + "} dlig;\n"
    scratch = _copy(font)
    del scratch["GSUB"]
    addOpenTypeFeaturesFromString(scratch, fea_text, tables=["GSUB"])
    new_table, gsub = scratch["GSUB"].table, font["GSUB"].table
    offset = len(gsub.LookupList.Lookup)
    for lookup in new_table.LookupList.Lookup:
        for st_ in lookup.SubTable:
            holders = [st_] + [rule for sets in ("ChainSubRuleSet", "ChainSubClassSet")
                               for rs in getattr(st_, sets, None) or [] if rs
                               for rule in (getattr(rs, "ChainSubRule", None)
                                            or getattr(rs, "ChainSubClassRule", None) or [])]
            for rule in holders:
                for rec in getattr(rule, "SubstLookupRecord", None) or []:
                    rec.LookupListIndex += offset
        gsub.LookupList.Lookup.append(lookup)
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    record = next(r for r in new_table.FeatureList.FeatureRecord if r.FeatureTag == "dlig")
    add_feature(gsub, "dlig", [i + offset for i in record.Feature.LookupListIndex])
    return shift, copies


def extend_kern(font, pairs):
    """A further pair lookup in `kern`, for trying pairs before they join the rest."""
    if not pairs:
        return
    gpos = font["GPOS"].table
    gpos.LookupList.Lookup.append(buildLookup(buildPairPosGlyphs(
        {k: (buildValue({"XAdvance": v}), None) for k, v in pairs.items()},
        font.getReverseGlyphMap()), flags=0x0008))
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    for r in gpos.FeatureList.FeatureRecord:
        if r.FeatureTag == "kern":
            r.Feature.LookupListIndex.append(len(gpos.LookupList.Lookup) - 1)


def dlig_kerning(font, inventory, cases, copies):
    """Segoe's kerning against its `dlig` copies, from the measurements with
    kerning on: against what follows a copy, from each copy-and-character text;
    against what comes before, from each character-before-it text. A glyph that
    begins with a measured character takes that character's pair. Returns the
    pairs in units, and the residual per measured text (units) once they are in,
    which the gate holds to Segoe's."""
    width = {c["text"]: units(c["width"]) for c in cases
             if c["group"] == "dlig" and c["features"] == {"dlig": 1}}
    ligatures, contexts = segoe_dlig(inventory)
    on = {"dlig": True}
    pairs = {}

    def shape_with(p):
        trial = _copy(font)
        extend_kern(trial, p)
        return shaper(trial)

    shape = shape_with(pairs)
    right = {}
    for text in width:
        if len(text) == 2 and any(text[0] in f and text[1] in a for f, a in contexts):
            glyphs, w = shape(text, on)
            if len(glyphs) == 2 and glyphs[0][0] in copies:
                right[text] = (glyphs[0][0], width[text] - w)
    found = {}
    for text in width:
        glyphs, _ = shape(text, on)
        for (g, c), (h, d) in zip(glyphs, glyphs[1:]):
            core = text[c] + text[d]
            if g in copies and core in right:
                found.setdefault((g, h), set()).add(right[core][1])
    for key, vals in found.items():
        if max(vals) - min(vals) > 1:
            raise SystemExit(f"dlig kerning {key} needs {sorted(vals)}")
        if v := round(st.median(vals)):
            pairs[key] = v
    shape = shape_with(pairs)
    found = {}
    for text in width:
        glyphs, w = shape(text, on)
        if len(glyphs) >= 2 and glyphs[1][0] in copies and glyphs[1][1] == 1:
            found.setdefault((glyphs[0][0], glyphs[1][0]), []).append(width[text] - w)
    for key, vals in found.items():
        if max(vals) - min(vals) > 1:
            raise SystemExit(f"dlig kerning {key} needs {sorted(vals)}")
        if v := round(st.median(vals)):
            pairs[key] = v
    shape = shape_with(pairs)
    residual = {text: target - shape(text, on)[1] for text, target in width.items()}
    dlig_sweep(shape, ligatures, contexts, font.getBestCmap())
    return pairs, residual


def dlig_sweep(shape, ligatures, contexts, cmap):
    """dlig must change nothing Segoe's does not: every pair of printable ASCII,
    dlig characters and spacing accents that holds none of Segoe's sequences or
    contexts shapes to the same glyphs, at the same width, with dlig on and off,
    with kerning and the default ligatures on and off."""
    chars = sorted({chr(c) for c in range(32, 127)} | {ch for q in ligatures for ch in q}
                   | {ch for f, a in contexts for ch in f | a} | {chr(c) for c in dotless_before()})
    chars = [ch for ch in chars if ord(ch) in cmap]
    moved = []
    for base in ({}, {"kern": False}, {"liga": False, "clig": False}):
        for x in chars:
            for y in chars:
                text = x + y
                if any(q in text for q in ligatures) or any(x in f and y in a for f, a in contexts):
                    continue
                if shape(text, base) != shape(text, {**base, "dlig": True}):
                    moved.append((text, base))
    if moved:
        raise SystemExit(f"dlig changes text outside Segoe's contexts: {moved[:8]}")


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
    inventory, cases, marks = segoe_features(size, w)
    dotless_added = extend_dotless(font)
    ccmp_shift, ccmp_copies = ccmp_widths(font, shift, source_adv, seg, marks, cases)
    shift.update(ccmp_shift)
    shift.update(space_marks(font, marks, shift))
    shift.update(frac_widths(font, cases, shift))
    dlig_shift, dlig_copies = dlig_substitution(font, inventory, cases, lig_components, shift,
                                                source_adv)
    shift.update(dlig_shift)
    pruned = prune(font)
    move_anchors(font, shift)
    unmarked = unmark(font, target)
    pairs = kern_pairs(font, target, seg, lig_components)
    inside = {g: v for g, cps in lig_components.items()
              if (v := internal_kern(seg, cps, font["hmtx"][g][0]))}
    trial = _copy(font)
    add_kern(trial, pairs, inside)
    dlig_pairs, residual = dlig_kerning(trial, inventory, cases, dlig_copies)
    if dlig_pairs.keys() & pairs.keys():
        raise SystemExit("a dlig pair is also a Segoe pair; the trial added them, the font would not")
    pairs.update({k: (buildValue({"XAdvance": v}), None) for k, v in dlig_pairs.items()})
    add_kern(font, pairs, inside)
    metrics_and_names(font, size, w)
    out = face_path(size, w)
    font.save(out)
    report = {"wght": wght, "wdth": wdth, "clamped": clamped, "kern_pairs": len(pairs),
              "unmarked": unmarked, "ligatures": sorted(lig_shift), "copies": lig_copies,
              "ligatures_skipped": lig_skipped, "ccmp_copies": ccmp_copies, "pruned": pruned,
              "dlig_pairs": len(dlig_pairs), "dotless_added": dotless_added,
              "dlig_off": {k: v for k, v in residual.items() if v},
              "overlaps": overlaps(TTFont(out), target, seg)}
    point = {"wght": wght, "wdth": wdth, "clamped": clamped,
             "copies": {**lig_copies, **tnum_copies, **ccmp_copies, **dlig_copies}}
    return face_name(size, w), report, point


def build():
    DIST.mkdir(exist_ok=True)
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(build_face, FACES))
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build/v0_3-report.json").write_text(
        json.dumps({name: report for name, report, _ in results}, indent=1) + "\n")
    # What the gate checks rather than trusts; committed, and compared with HEAD.
    (ROOT / "data/v0_3/build.json").write_text(json.dumps(
        {name: point for name, _, point in results}, indent=1, sort_keys=True) + "\n")
    sums = "".join(f"{hashlib.sha256(face_path(*f).read_bytes()).hexdigest()}  "
                   f"{face_path(*f).relative_to(ROOT)}\n" for f in FACES)
    (ROOT / "SHA256SUMS").write_text(sums)
    for name, report, _ in results:
        print(name, json.dumps({k: report[k] for k in ("wght", "wdth", "clamped", "kern_pairs",
                                                       "ccmp_copies", "dlig_pairs")}),
              "pruned:", len(report["pruned"]), "dlig off:", report["dlig_off"],
              "overlaps:", "".join(chr(c) for c in report["overlaps"]))


if __name__ == "__main__":
    build()
