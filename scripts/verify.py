# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""The gate, v0.2. v0.1's Done-when checks 1-7 run on each of the fifteen faces
and print one line each, prefixed with the face; 8 (reproducible), 9 (tables,
per face) and 10 (the face set) are v0.2's. Any failure, including an error
inside a check, makes the exit status non-zero. The last line is `gate: PASS`
or `gate: FAIL`.

The gate does not take its expectations from scripts/build.py. The values the
spec fixes are written here, the Open Sans reference is instanced and
decomposed here, and the overlap criterion is computed here. What it reads from
the build is the fonts, and data/v0_2/build.json (each face's chosen point and
glyph copies), whose claims it checks rather than trusts. It writes each face's
compiled Open Sans reference to build/verify-reference-<face>.ttf for shaping.

Usage: python scripts/verify.py [--no-rebuild]

Without --no-rebuild the gate builds twice and compares the bytes with each
other and with SHA256SUMS as committed at HEAD.
"""
import hashlib
import io
import json
import statistics as st
import subprocess
import sys
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otBase
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
OPEN_SANS = ROOT / "sources/opensans/OpenSans[wdth,wght].ttf"
TARGET = ROOT / "data/v0_1/segoe-ui-variable.json"
SEGOE = ROOT / "data/v0_2/segoe"
POINTS = ROOT / "data/v0_2/build.json"
ALLOW = ROOT / "data/v0_2/overlaps.json"
STRINGS = ROOT / "probe/v0/strings.json"

# PLAN.md, written out rather than imported: v0.1 scope item 5, and v0.2's faces and names.
UPM = 2048
PX = UPM / 1000
METRICS = {"hhea.ascent": 2210, "hhea.descent": -514, "hhea.lineGap": 0,
           "OS/2.sTypoAscender": 1491, "OS/2.sTypoDescender": -431, "OS/2.sTypoLineGap": 269,
           "OS/2.usWinAscent": 2210, "OS/2.usWinDescent": 514}
SIZES = ("Small", "Text", "Display")
WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
FACES = [(size, w) for size in SIZES for w in WEIGHTS]
# v0.1 scope item 4: spacing accents Open Sans classes as marks, made base glyphs.
UNMARKED = (0x0384, 0x0385, 0x1FDE)


def face_key(size, w):
    return f"{size}-{WEIGHTS[w]}"


def font_path(size, w):
    return ROOT / "dist" / f"HarenaUI-{size}{WEIGHTS[w]}.ttf"


def names(size, w):
    family, style = f"Harena UI {size}", WEIGHTS[w]
    ribbi = style in ("Regular", "Bold")
    ps = f"HarenaUI{size}-{style}"
    return {
        0: "Copyright 2020 The Open Sans Project Authors (https://github.com/googlefonts/opensans)\n"
           "Copyright 2026 Jeeyong Um",
        1: family if ribbi else f"{family} {style}", 2: style if ribbi else "Regular",
        3: f"0.2.0;HRNA;{ps}", 4: f"{family} {style}", 5: "Version 0.2.0", 6: ps,
        13: "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
            "This license is available with a FAQ at: https://openfontlicense.org",
        14: "https://openfontlicense.org", 16: family, 17: style,
    }


FORBIDDEN = ("segoe", "selawik", "source", "pretendard")
# Scope item 2's point: median ink width equal, within rounding wdth to 0.1; and
# the integer wght whose compiled stem is nearest Segoe's within STEM_WINDOW of
# it (a compiled stem jitters by a unit as wght rises, so neighbours are not
# enough).
INK_RATIO_TOL = 0.005
STEM_WINDOW = 15
_L_SOURCE = []


def l_stem(wght, wdth):
    """The `l` stem, in px at 1000 px, of the compiled Open Sans instance; from a
    source subset to `l`, which instances and compiles the glyph as the full font."""
    from fontTools import subset
    if not _L_SOURCE:
        f = TTFont(OPEN_SANS)
        opts = subset.Options()
        opts.layout_features = []
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=[ord("l")])
        sub.subset(f)
        _L_SOURCE.append(_bytes(f))
    f = compiled(instantiateVariableFont(TTFont(io.BytesIO(_L_SOURCE[0])), {"wght": wght, "wdth": wdth},
                                         updateFontNames=False))
    lo, hi = ink_x(f, f.getBestCmap()[ord("l")])
    return (hi - lo) / PX

failed = []
lines = []


def check(name, ok, detail=""):
    lines.append(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))
    if not ok:
        failed.append(name)


def guarded(name, fn):
    try:
        fn()
    except Exception as e:  # a check that cannot run has failed
        check(name, False, f"error: {e!r}")


def _bytes(font):
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def compiled(font):
    buf = io.BytesIO()
    font.save(buf)
    buf.seek(0)
    return TTFont(buf)


def outline(font, glyph, decompose):
    gs = font.getGlyphSet()
    pen = DecomposingRecordingPen(gs) if decompose else RecordingPen()
    gs[glyph].draw(pen)
    return pen.value


def ink_x(font, glyph):
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    gs[glyph].draw(pen)
    return None if pen.bounds is None else (pen.bounds[0], pen.bounds[2])


def shaper(path):
    font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))

    def width(text, direction=None):
        return sum(p.x_advance for _, p in shape(text, direction))

    def shape(text, direction=None):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        if direction:
            buf.direction = direction
        hb.shape(font, buf, {"kern": True})
        return list(zip(buf.glyph_infos, buf.glyph_positions))
    width.shape = shape
    return width


def pair_width(width, a, b):
    """A pair's width as the browser measured it: in a left-to-right paragraph,
    where a neutral beside a right-to-left letter resolves left-to-right and is
    a run of its own, not mirrored. Letting HarfBuzz guess the direction of the
    whole pair instead would mirror `(` into `)`, which Segoe gives a different
    advance in Display."""
    rtl = [unicodedata.bidirectional(chr(c)) in ("R", "AL") for c in (a, b)]
    if all(rtl):
        return width(chr(a) + chr(b), "rtl")
    if any(rtl):
        return width(chr(a)) + width(chr(b))
    return width(chr(a) + chr(b), "ltr")


def ligatures(font):
    """{ligature glyph: component code points} for default-on ligature features,
    read from the font's GSUB, for ligatures whose components are all mapped."""
    by_glyph = {g: cp for cp, g in font.getBestCmap().items()}
    gsub = font["GSUB"].table
    on = {i for r in gsub.FeatureList.FeatureRecord if r.FeatureTag in ("liga", "clig", "rlig")
          for i in r.Feature.LookupListIndex}
    out = {}
    for i in on:
        lookup = gsub.LookupList.Lookup[i]
        for t in lookup.SubTable:
            t = t.ExtSubTable if lookup.LookupType == 7 else t
            for first, ligs in t.ligatures.items():
                for lig in ligs:
                    cps = [by_glyph.get(g) for g in [first] + list(lig.Component)]
                    if None not in cps:
                        out[lig.LigGlyph] = cps
    return out


def attaches(font, base, mark):
    """Whether a mark-to-base or mark-to-ligature lookup in the font's GPOS
    attaches this mark to this base: both covered, and the base has an anchor for
    the mark's class."""
    gpos = font["GPOS"].table
    for lookup in gpos.LookupList.Lookup:
        for t in lookup.SubTable:
            kind = lookup.LookupType
            if kind == 9:
                t, kind = t.ExtSubTable, t.ExtSubTable.LookupType
            if kind not in (4, 5) or mark not in t.MarkCoverage.glyphs:
                continue
            cls = t.MarkArray.MarkRecord[t.MarkCoverage.glyphs.index(mark)].Class
            if kind == 4 and base in t.BaseCoverage.glyphs:
                if t.BaseArray.BaseRecord[t.BaseCoverage.glyphs.index(base)].BaseAnchor[cls] is not None:
                    return True
            if kind == 5 and base in t.LigatureCoverage.glyphs:
                attach = t.LigatureArray.LigatureAttach[t.LigatureCoverage.glyphs.index(base)]
                if any(c.LigatureAnchor[cls] is not None for c in attach.ComponentRecord):
                    return True
    return False


MARKS = [0x0300, 0x0301, 0x0302, 0x0303, 0x0304, 0x0306, 0x0308, 0x030A, 0x030C, 0x0323, 0x0327, 0x0328]


def reproducible():
    paths = [font_path(*f) for f in FACES]
    hashes = []
    for _ in range(2):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/build.py")], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"build failed: {r.stderr.strip().splitlines()[-1:]}")
        hashes.append([hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])

    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).returncode

    tracked = ("SHA256SUMS", "data/v0_2/build.json")
    committed = all(git("cat-file", "-e", f"HEAD:{p}") == 0 for p in tracked)
    same_as_head = git("diff", "--quiet", "HEAD", "--", *tracked) == 0
    want = "".join(f"{h}  {p.relative_to(ROOT)}\n" for h, p in zip(hashes[0], paths))
    listed = (ROOT / "SHA256SUMS").read_text() == want
    check("8 reproducible", hashes[0] == hashes[1] and committed and same_as_head and listed,
          f"two builds of {len(paths)} faces {'identical' if hashes[0] == hashes[1] else 'differ'}; "
          + ("SHA256SUMS lists them" if listed else "SHA256SUMS does not list exactly these") + "; "
          + ("not committed" if not committed else
             "SHA256SUMS and build.json equal HEAD's" if same_as_head else "differ from HEAD"))


def faces():
    """Check 10: exactly the fifteen files, upright, static, with the weight and
    style bits PLAN.md v0.2 gives each. Names are check 6, per face."""
    want = {font_path(*f).name for f in FACES}
    have = {p.name for p in (ROOT / "dist").glob("*") if p.is_file()}
    bad = [f"missing {sorted(want - have)}"] if want - have else []
    bad += [f"unexpected {sorted(have - want)}"] if have - want else []
    for size, w in FACES:
        if not font_path(size, w).exists():
            continue
        f = TTFont(font_path(size, w))
        bold = WEIGHTS[w] == "Bold"
        sel, mac = f["OS/2"].fsSelection, f["head"].macStyle
        off = []
        if f["OS/2"].usWeightClass != w:
            off.append(f"usWeightClass {f['OS/2'].usWeightClass}")
        if f["OS/2"].usWidthClass != 5:
            off.append(f"usWidthClass {f['OS/2'].usWidthClass}")
        if sel & 1 or sel & (1 << 9) or mac & 2 or f["post"].italicAngle != 0 \
                or f["hhea"].caretSlopeRun != 0 or f["hhea"].caretSlopeRise <= 0 \
                or f["OS/2"].panose.bLetterForm >= 9:  # PANOSE letterforms 9-15 are oblique
            off.append("italic or oblique")
        if sel & (1 << 8):
            off.append("WWS set, though the families are optical sizes")
        if bool(sel & (1 << 5)) != bold or bool(sel & (1 << 6)) == bold or bool(mac & 1) != bold:
            off.append(f"style bits fsSelection {sel:#06x} macStyle {mac:#06x}")
        off += [f"has {t}" for t in ("fvar", "gvar", "avar", "STAT", "HVAR", "MVAR") if t in f]
        if off:
            bad.append(f"{face_key(size, w)}: {off}")
    check("10 faces", not bad, f"{len(want)} faces, upright and static, weight and style bits as "
          "specified" if not bad else f"{bad[:6]}")


# --- check 9: GSUB, GPOS and GDEF are Open Sans' apart from the known edits ------


def unwrap(table):
    """Replace extension lookups by what they wrap, so the comparison does not
    depend on how the compiler packed a table."""
    for lookup in table.LookupList.Lookup:
        if lookup.LookupType in (7, 9) and type(table).__name__ in ("GSUB", "GPOS") and \
                lookup.LookupType == (7 if type(table).__name__ == "GSUB" else 9):
            lookup.SubTable = [st_.ExtSubTable for st_ in lookup.SubTable]
            lookup.LookupType = lookup.SubTable[0].LookupType


def canon(x):
    """A plain-data form of an OpenType layout table, without counts and
    offsets, which compilation derives."""
    if isinstance(x, (otBase.BaseTable, otBase.FormatSwitchingBaseTable)):
        x.ensureDecompiled()
        return (type(x).__name__, {k: canon(v) for k, v in sorted(vars(x).items())
                                   if not k.endswith("Count") and not k.startswith("_")
                                   and k not in ("reader", "font")})
    if isinstance(x, dict):
        return {k: canon(v) for k, v in sorted(x.items())}
    if isinstance(x, (list, tuple)):
        return [canon(v) for v in x]
    return x


def features_and_scripts(table, drop_tag=""):
    """FeatureList and ScriptList with feature indices resolved to (tag, lookup
    indices), so removing a feature does not renumber the others."""
    recs = table.FeatureList.FeatureRecord
    resolved = [(r.FeatureTag, tuple(r.Feature.LookupListIndex), repr(canon(r.Feature.FeatureParams)))
                for r in recs]
    feats = [f for f in resolved if f[0] != drop_tag]
    scripts = {}
    for sr in table.ScriptList.ScriptRecord:
        systems = [("dflt", sr.Script.DefaultLangSys)] + [(r.LangSysTag, r.LangSys) for r in sr.Script.LangSysRecord]
        for tag, ls in systems:
            if ls is None:
                continue
            req = ls.ReqFeatureIndex
            scripts[(sr.ScriptTag, tag)] = (
                None if req == 0xFFFF else resolved[req],
                [resolved[i] for i in ls.FeatureIndex if resolved[i][0] != drop_tag])
    return feats, scripts


def mark_subtables(table):
    for lookup in table.LookupList.Lookup:
        for t in lookup.SubTable:
            if lookup.LookupType in (4, 5, 6):
                yield lookup.LookupType, t


def mark_parts(kind, t):
    """(coverage, records, anchors of a record) for each glyph list a mark
    subtable has."""
    if kind == 4:
        return [(t.MarkCoverage, t.MarkArray.MarkRecord, lambda r: [r.MarkAnchor]),
                (t.BaseCoverage, t.BaseArray.BaseRecord, lambda r: r.BaseAnchor)]
    if kind == 5:
        return [(t.MarkCoverage, t.MarkArray.MarkRecord, lambda r: [r.MarkAnchor]),
                (t.LigatureCoverage, t.LigatureArray.LigatureAttach,
                 lambda r: [a for c in r.ComponentRecord for a in c.LigatureAnchor])]
    return [(t.Mark1Coverage, t.Mark1Array.MarkRecord, lambda r: [r.MarkAnchor]),
            (t.Mark2Coverage, t.Mark2Array.Mark2Record, lambda r: r.Mark2Anchor)]


def drop_glyphs(cov, recs, glyphs):
    keep = [i for i, g in enumerate(cov.glyphs) if g not in glyphs]
    cov.glyphs[:] = [cov.glyphs[i] for i in keep]
    recs[:] = [recs[i] for i in keep]


def tables_equal(font, ref, copies, dxs):
    """Normalise the known edits away and compare. On the font's side: the kern
    feature and its lookup are removed; every anchor is moved back by its glyph's
    shift; each copy's GSUB references are renamed to its original only where the
    build puts them (a `.liga` copy as a default ligature's output, a `.tnum`
    copy as `tnum`'s output, whose entry from the original is dropped), and any
    other occurrence fails; its mark records and GDEF class, once shown equal to
    the original's, are dropped. On Open Sans' side: the three spacing accents leave mark attachment
    and become base glyphs. Returns a list of differences."""
    out = []
    rcmap = ref.getBestCmap()
    accents = {rcmap[cp] for cp in UNMARKED}
    for tag in ("GSUB", "GPOS", "GDEF"):
        for f in (font, ref):
            f[tag].table.ensureDecompiled(recurse=True)
    gsub, rgsub = font["GSUB"].table, ref["GSUB"].table
    gpos, rgpos = font["GPOS"].table, ref["GPOS"].table
    for t in (gsub, rgsub, gpos, rgpos):
        unwrap(t)

    # GSUB: a copy may appear only where the build puts it — a `.liga` copy as the
    # output of a default ligature, a `.tnum` copy as the output of `tnum` — and is
    # renamed back only there. `tnum`'s entry from the original to its copy is the
    # one added; the rest must then be Open Sans'.
    on = {}
    for r in gsub.FeatureList.FeatureRecord:
        for i in r.Feature.LookupListIndex:
            on.setdefault(i, set()).add(r.FeatureTag)
    misplaced = []
    for i, lookup in enumerate(gsub.LookupList.Lookup):
        tags = on.get(i, set())
        for t in lookup.SubTable:
            if lookup.LookupType == 4:
                for ligs in t.ligatures.values():
                    for lig in ligs:
                        if lig.LigGlyph in copies:
                            if lig.LigGlyph.endswith(".liga") and tags and tags <= {"liga", "clig", "rlig"}:
                                lig.LigGlyph = copies[lig.LigGlyph]
                            else:
                                misplaced.append((i, lig.LigGlyph))
            elif lookup.LookupType == 1:
                for k, v in list(t.mapping.items()):
                    if v in copies:
                        if v.endswith(".tnum") and tags == {"tnum"}:
                            if k == copies[v]:
                                del t.mapping[k]
                            else:
                                t.mapping[k] = copies[v]
                        else:
                            misplaced.append((i, v))

    def names_in(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for k, v in x.items():
                yield from names_in(k)
                yield from names_in(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                yield from names_in(v)
    ours = canon(gsub.LookupList)
    misplaced += sorted({n for n in names_in(ours) if n in copies})
    if misplaced:
        out.append(f"copies used outside their feature: {misplaced[:6]}")
    if ours != canon(rgsub.LookupList):
        diff = [i for i, (a, b) in enumerate(zip(ours[1]["Lookup"], canon(rgsub.LookupList)[1]["Lookup"])) if a != b]
        out.append(f"GSUB lookups differ: {diff[:6] or 'count'}")
    if features_and_scripts(gsub) != features_and_scripts(rgsub):
        out.append("GSUB features or scripts differ")
    for tag, a, b in (("GSUB", gsub, rgsub), ("GPOS", gpos, rgpos)):
        if a.Version != b.Version or canon(getattr(a, "FeatureVariations", None)) != \
                canon(getattr(b, "FeatureVariations", None)):
            out.append(f"{tag} version or feature variations differ")

    # GPOS: the kern feature is one lookup, appended last
    kern = [r for r in gpos.FeatureList.FeatureRecord if r.FeatureTag == "kern"]
    last = len(gpos.LookupList.Lookup) - 1
    if len(kern) != 1 or list(kern[0].Feature.LookupListIndex) != [last]:
        out.append("GPOS kern is not one feature on the last lookup")
    else:
        gpos.LookupList.Lookup.pop()
        k = gpos.FeatureList.FeatureRecord.index(kern[0])
        for sr in gpos.ScriptList.ScriptRecord:
            for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
                if ls is not None and k not in ls.FeatureIndex:
                    out.append(f"kern is missing from a language system of {sr.ScriptTag}")
    if any(r.FeatureTag == "kern" for r in rgpos.FeatureList.FeatureRecord):
        out.append("Open Sans has a kern feature")
    if features_and_scripts(gpos, "kern") != features_and_scripts(rgpos):
        out.append("GPOS features or scripts differ beyond kern")
    copy_bad = []
    for kind, t in mark_subtables(gpos):
        for cov, recs, anchors in mark_parts(kind, t):
            for g, r in zip(cov.glyphs, recs):
                for a in anchors(r):
                    if a is not None:
                        a.XCoordinate -= dxs.get(g, 0)
            for c, orig in copies.items():
                if (c in cov.glyphs) != (orig in cov.glyphs):
                    copy_bad.append(c)
                elif c in cov.glyphs and canon(recs[cov.glyphs.index(c)]) != canon(recs[cov.glyphs.index(orig)]):
                    copy_bad.append(c)
            drop_glyphs(cov, recs, set(copies))
    for kind, t in mark_subtables(rgpos):
        for cov, recs, _ in mark_parts(kind, t)[:1] + (mark_parts(kind, t)[1:] if kind == 6 else []):
            drop_glyphs(cov, recs, accents)
    if copy_bad:
        out.append(f"copies' mark records differ from their originals': {sorted(set(copy_bad))}")
    ours, theirs = canon(gpos.LookupList), canon(rgpos.LookupList)
    if ours != theirs:
        diff = [i for i, (a, b) in enumerate(zip(ours[1]["Lookup"], theirs[1]["Lookup"])) if a != b]
        out.append(f"GPOS lookups differ: {diff[:6] or 'count'}")

    # GDEF
    gdef, rgdef = font["GDEF"].table, ref["GDEF"].table
    classes = gdef.GlyphClassDef.classDefs
    bad = [c for c, o in copies.items() if classes.get(c) != classes.get(o)]
    if bad:
        out.append(f"copies' GDEF class differs: {bad}")
    for c in copies:
        classes.pop(c, None)
    for g in accents:
        rgdef.GlyphClassDef.classDefs[g] = 1
    sets = getattr(rgdef, "MarkGlyphSetsDef", None)
    for cov in (sets.Coverage if sets else []):
        cov.glyphs = [g for g in cov.glyphs if g not in accents]
    if canon(gdef) != canon(rgdef):
        out.append("GDEF differs")
    return out


def face(size, w):
    """Checks 1-7 and 9 for one face. Returns (lines, failed)."""
    lines.clear()  # a pool worker runs several faces; report each one's own
    failed.clear()
    key = face_key(size, w)
    FONT = font_path(size, w)
    REF_PATH = ROOT / f"build/verify-reference-{key}.ttf"
    try:
        doc = json.loads(TARGET.read_text())
        target = doc["target"]
        seg = json.loads((SEGOE / f"{key}.json").read_text())
        point = json.loads(POINTS.read_text())[key]
        font = TTFont(FONT)
        ref = compiled(instantiateVariableFont(
            TTFont(OPEN_SANS), {"wght": point["wght"], "wdth": point["wdth"]}, updateFontNames=False))
        cmap, rcmap, hmtx = font.getBestCmap(), ref.getBestCmap(), font["hmtx"]
        REF_PATH.parent.mkdir(exist_ok=True)
        REF_PATH.write_bytes(_bytes(ref))
        copies = point["copies"]
        width = shaper(FONT)
    except Exception as e:
        check(f"{key} inputs", False, f"error: {e!r}")
        return lines, failed
    dxs = {}

    def c1():
        bad = [cp for cp in target if cp not in cmap
               or abs(hmtx[cmap[cp]][0] - seg["advance"][str(cp)] * PX) > 0.5]
        targets = {cmap[cp] for cp in target if cp in cmap}
        rest = [g for g in ref.getGlyphOrder() if g not in targets]
        others = [g for g in rest if g not in hmtx.metrics or hmtx[g][0] != ref["hmtx"][g][0]]
        check(f"{key} 1 advances", not bad and not others,
              f"{len(target) - len(bad)}/{len(target)} target glyphs at Segoe's advance; "
              f"{len(rest) - len(others)}/{len(rest)} others at Open Sans'"
              + (f"; off: {''.join(chr(c) for c in bad[:20])}" if bad else "")
              + (f"; others changed: {others[:10]}" if others else ""))
    guarded(f"{key} 1 advances", c1)

    def c2():
        letters = doc["kern_pairs_from"]
        adv = {cp: seg["advance"][str(cp)] for cp in letters}
        kern = seg["kern"]
        bad, kerned, plain = [], 0, 0
        for a in letters:
            for b in letters:
                k = kern.get(f"{a},{b}", 0.0)
                d = pair_width(width, a, b) - (adv[a] + adv[b] + k) * PX
                if abs(d) > 0.5:
                    bad.append((a, b, d))
                elif k:
                    kerned += 1
                else:
                    plain += 1
        # Runs that form a ligature, after and before every letter: the width must
        # be Segoe's for the same characters.
        ligs = ligatures(font)
        seq = lambda cps: sum(seg["advance"][str(c)] for c in cps) + sum(
            kern.get(f"{a},{b}", 0.0) for a, b in zip(cps, cps[1:]))
        runs = 0
        for cps in ligs.values():
            text = "".join(map(chr, cps))
            for x in letters:
                for t, cps2 in ((chr(x) + text, [x] + cps), (text + chr(x), cps + [x])):
                    d = width(t) - seq(cps2) * PX
                    runs += 1
                    if abs(d) > 0.5:
                        bad.append((cps2[0], cps2[-1], d))
        # Every pair in the font's kern feature must be a measured Segoe pair, or
        # stand for one through a ligature's first or last component.
        by_glyph = {g: cp for cp, g in cmap.items()}
        gpos = font["GPOS"].table
        idx = {i for r in gpos.FeatureList.FeatureRecord if r.FeatureTag == "kern"
               for i in r.Feature.LookupListIndex}
        stray = []
        for i in idx:
            lookup = gpos.LookupList.Lookup[i]
            for t in lookup.SubTable:
                t = t.ExtSubTable if lookup.LookupType == 9 else t
                if t.Format != 1:
                    raise RuntimeError("kern uses PairPos format 2; extend this check")
                # Advance only: no placement, nothing on the second glyph, marks skipped.
                if t.ValueFormat1 != 0x0004 or t.ValueFormat2 != 0 or lookup.LookupFlag != 0x0008:
                    stray.append(("value formats", t.ValueFormat1, t.ValueFormat2, lookup.LookupFlag))
                for first, ps in zip(t.Coverage.glyphs, t.PairSet):
                    for rec in ps.PairValueRecord:
                        a = by_glyph.get(first)
                        if a is None and first in ligs:
                            a = ligs[first][-1]
                        b = by_glyph.get(rec.SecondGlyph)
                        if b is None and rec.SecondGlyph in ligs:
                            b = ligs[rec.SecondGlyph][0]
                        if a is None or b is None or f"{a},{b}" not in kern:
                            stray.append((first, rec.SecondGlyph))
        check(f"{key} 2 kerning", not bad and not stray,
              f"{kerned} kerned and {plain} unkerned pairs and {runs} ligature runs within 0.5 units; "
              f"{len(stray) or 'no'} kern pairs beyond Segoe's"
              + ("; off, e.g. " + ", ".join(f"{chr(a)}{chr(b)} {d:+.1f}" for a, b, d in bad[:8]) if bad else "")
              + (f"; stray: {stray[:6]}" if stray else ""))
    guarded(f"{key} 2 kerning", c2)

    def c2t():
        tab = seg["tabular"]
        bad = []
        for digit, px in tab.items():
            buf = hb.Buffer()
            buf.add_str(chr(int(digit)))
            buf.guess_segment_properties()
            hb.shape(tnum_font, buf, {"tnum": True, "kern": True})
            got = sum(p.x_advance for p in buf.glyph_positions)
            if abs(got - px * PX) > 0.5:
                bad.append(f"{chr(int(digit))} {got} vs {px * PX:.1f}")
        check(f"{key} 2t tabular digits", not bad, f"{len(tab) - len(bad)}/{len(tab)} digits at Segoe's tabular advance "
              "under tnum" + (f"; off: {bad}" if bad else ""))
    tnum_font = hb.Font(hb.Face(hb.Blob.from_file_path(str(FONT))))
    guarded(f"{key} 2t tabular digits", c2t)

    def c3():
        strings = [s for g in json.loads(STRINGS.read_text()).values() for s in g]
        errs = [(s, (width(s) / PX - seg["strings"][s][0]) / seg["strings"][s][0]) for s in strings]
        worst = max(errs, key=lambda e: abs(e[1]))
        check(f"{key} 3 strings", abs(worst[1]) <= 0.001,
              f"{len(strings)} strings, worst {100 * worst[1]:+.3f}% ({worst[0]!r})")
    guarded(f"{key} 3 strings", c3)

    def c4():
        got = {k: getattr(font[k.split(".")[0]], k.split(".")[1]) for k in METRICS}
        off = [f"{k} {got[k]}" for k in METRICS if got[k] != METRICS[k]]
        if font["OS/2"].fsSelection & (1 << 7):
            off.append("USE_TYPO_METRICS set")
        if font["head"].unitsPerEm != UPM:
            off.append(f"unitsPerEm {font['head'].unitsPerEm}")
        check(f"{key} 4 vertical metrics", not off, "as specified" if not off else f"differ: {off}")
    guarded(f"{key} 4 vertical metrics", c4)

    def c5():
        bad = []
        # The chosen point satisfies scope item 2, measured here.
        target_stem = seg["stems"]["l"]
        lo, hi = ink_x(ref, rcmap[ord("l")])
        stem = (hi - lo) / PX
        ratios = []
        for cp in target:
            row, b = seg["ink"].get(str(cp)), ink_x(ref, rcmap[cp])
            if row and b and b[1] > b[0]:
                ratios.append((row[1] - row[0]) / ((b[1] - b[0]) / PX))
        ratio = st.median(ratios)
        # wght is an integer, and no integer within STEM_WINDOW of it gives a
        # compiled stem nearer Segoe's (a compiled stem jitters by a unit, so a
        # local check is not enough). Where Segoe's stem is beyond Open Sans'
        # range, the point stops at the axis' end (PLAN.md v0.2, Light).
        axes = {a.axisTag: (a.minValue, a.maxValue) for a in TTFont(OPEN_SANS)["fvar"].axes}
        wmin, wmax = axes["wght"]
        if not isinstance(point["wght"], int):
            bad.append(f"wght {point['wght']} is not an integer")
        else:
            own = abs(stem - target_stem)
            for nw in range(max(int(wmin), point["wght"] - STEM_WINDOW),
                            min(int(wmax), point["wght"] + STEM_WINDOW) + 1):
                if abs(l_stem(nw, point["wdth"]) - target_stem) < own - 1e-9:
                    bad.append(f"stem {stem:.2f} px against {target_stem}: wght {nw} is nearer")
                    break
        clamped = (point["wght"] == wmin and stem > target_stem) or \
                  (point["wght"] == wmax and stem < target_stem)
        if ("wght" in point["clamped"]) != clamped:
            bad.append(f"build.json says clamped {point['clamped']}, stem {stem:.2f}/{target_stem}")
        dmin, dmax = axes["wdth"]
        wdth_clamped = (point["wdth"] == dmax and ratio > 1) or (point["wdth"] == dmin and ratio < 1)
        if ("wdth" in point["clamped"]) != wdth_clamped:
            bad.append(f"build.json says clamped {point['clamped']}, ink ratio {ratio:.4f}")
        if abs(ratio - 1) > INK_RATIO_TOL and not wdth_clamped:
            bad.append(f"median ink ratio {ratio:.4f}")
        if cmap != rcmap:
            diff = sorted(set(cmap.items()) ^ set(rcmap.items()))
            bad.append(f"cmap differs from Open Sans': {diff[:6]}")
        order = font.getGlyphOrder()
        n_ref = len(ref.getGlyphOrder())
        if order[:n_ref] != ref.getGlyphOrder() or set(order[n_ref:]) != set(copies):
            bad.append("glyph order is not Open Sans' plus the ligature copies")
        rset = set(ref.getGlyphOrder())
        for name in order:
            source = copies.get(name, name)
            if source not in rset:
                bad.append(f"{name}: not in Open Sans")
                continue
            if font["glyf"][name].isComposite():
                bad.append(f"{name}: composite")
                continue
            ours = outline(font, name, decompose=False)
            theirs = outline(ref, source, decompose=True)
            if [op for op, _ in ours] != [op for op, _ in theirs] \
                    or [len(a) for _, a in ours] != [len(a) for _, a in theirs]:
                bad.append(name)
                continue
            pts = [(p, q) for (_, a), (_, b) in zip(ours, theirs) for p, q in zip(a, b)]
            if pts:
                dx = pts[0][0][0] - pts[0][1][0]
                if any(p[0] - q[0] != dx or p[1] != q[1] for p, q in pts):
                    bad.append(name)
                else:
                    dxs[name] = dx
        # Placement (scope item 3): the ink sits where the leftover sidebearing
        # splits in Open Sans' own left:right ratio; where Open Sans' own
        # sidebearings are not both non-negative, the ink moves by half the change
        # in advance. A glyph whose advance did not change does not move. Copies
        # were placed in two roundings, so they may be off by one unit.
        misplaced = []
        for name, dx in dxs.items():
            source = copies.get(name, name)
            xmin, xmax = ink_x(ref, source)
            old, new = ref["hmtx"][source][0], hmtx[name][0]
            lsb, rsb = xmin, old - xmax
            if new == old and name not in copies:
                want = 0
            elif lsb >= 0 and rsb >= 0 and lsb + rsb > 0:
                want = round((new - (xmax - xmin)) * lsb / (lsb + rsb) - xmin)
            else:
                want = round((new - old) / 2)
            if abs(dx - want) > (1 if name in copies else 0):
                misplaced.append(f"{name} {dx:+d} vs {want:+d}")
        if misplaced:
            bad.append(f"misplaced: {misplaced[:6]}")
        n = len(order)
        check(f"{key} 5 outlines", not bad,
              f"{n - len(bad)}/{n} glyphs equal Open Sans at wght {point['wght']}, wdth {point['wdth']} "
              f"({len(copies)} copies), ink placed per the sidebearing split; stem {stem:.2f}/{target_stem} px, ink ratio {ratio:.4f}"
              + (f"; differ: {bad[:8]}" if bad else ""))
    guarded(f"{key} 5 outlines", c5)

    def c5b():
        ours, theirs = shaper(FONT).shape, shaper(REF_PATH).shape
        bases = [chr(cp) for cp in target if chr(cp).isalpha()]
        bases += ["".join(map(chr, cps)) for cps in ligatures(font).values()]

        def rel(shape, f, text):
            run = shape(text)
            if len(run) != 2:  # composed into one glyph, or not attached
                return None
            (gb, pb), (gm, pm) = run
            name = f.getGlyphOrder()[gb.codepoint]
            ink = ink_x(f, name)
            attached = attaches(f, name, f.getGlyphOrder()[gm.codepoint])
            # An attached mark is compared by where it sits on the base's ink; an
            # unattached one follows the advance, which is meant to change.
            return (attached, pb.x_advance + pm.x_offset - (ink[0] if ink else 0) if attached else 0,
                    pm.y_offset, f.getGlyphOrder()[gm.codepoint])
        bad, n = [], 0
        for base in bases:
            for m in MARKS:
                a, b = rel(ours, font, base + chr(m)), rel(theirs, ref, base + chr(m))
                if a is None and b is None:
                    continue
                n += 1
                if a != b:
                    bad.append(f"{base}+U+{m:04X} {a} vs {b}")
        check(f"{key} 5b marks", not bad, f"{n - len(bad)}/{n} base+mark clusters place the mark as Open Sans does "
              "relative to the base's ink" + (f"; differ: {bad[:4]}" if bad else ""))
    guarded(f"{key} 5b marks", c5b)

    def c6():
        recs = sorted((r.platformID, r.platEncID, r.langID, r.nameID, r.toUnicode()) for r in font["name"].names)
        want = sorted((3, 1, 0x409, nid, v) for nid, v in names(size, w).items())
        hits = [(r[3], w) for r in recs for w in FORBIDDEN if w in r[4].lower()]
        check(f"{key} 6 names", recs == want and not hits,
              "as specified" if recs == want and not hits else
              f"extra {[r[:4] for r in recs if r not in want]}, missing {[r[:4] for r in want if r not in recs]}, "
              f"forbidden {hits}")
    guarded(f"{key} 6 names", c6)

    def c7():
        allowed = set(json.loads(ALLOW.read_text())["faces"][key]["code_points"])
        found = set()
        for cp in target:
            row, b = seg["ink"].get(str(cp)), ink_x(font, cmap[cp])
            if not row or not b:
                continue
            ours = min(b[0], hmtx[cmap[cp]][0] - b[1]) / PX
            theirs = min(row[0], seg["advance"][str(cp)] - row[1])
            if ours < min(theirs, 0) - 5:
                found.add(cp)
        new, stale = found - allowed, allowed - found
        check(f"{key} 7 overlaps", not new and not stale, f"{len(found)} found"
              + (", all listed" if not new else "")
              + (f"; not listed: {''.join(chr(c) for c in sorted(new))}" if new else "")
              + (f"; listed but gone: {''.join(chr(c) for c in sorted(stale))}" if stale else ""))
    guarded(f"{key} 7 overlaps", c7)


    def c9():
        if not dxs:
            raise RuntimeError("check 5 did not establish each glyph's shift")
        bad = tables_equal(TTFont(FONT), compiled(TTFont(io.BytesIO(_bytes(ref)))), copies, dxs)
        check(f"{key} 9 tables", not bad, "GSUB, GPOS and GDEF equal Open Sans' apart from the "
              "known edits" if not bad else "; ".join(bad))
    guarded(f"{key} 9 tables", c9)
    return lines, failed


def main():
    if "--no-rebuild" in sys.argv:
        lines.append("SKIP 8 reproducible: --no-rebuild")
    else:
        guarded("8 reproducible", reproducible)
    guarded("10 faces", faces)
    print("\n".join(lines), flush=True)
    lines.clear()
    with ProcessPoolExecutor() as pool:
        for out, bad in pool.map(face, *zip(*FACES)):
            print("\n".join(out), flush=True)
            failed.extend(bad)
    print("gate:", "FAIL" if failed else "PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
