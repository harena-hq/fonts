# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""The gate, v0.4. v0.1's Done-when checks 1-7 run on each of the fifteen faces
and print one line each, prefixed with the face; 8 (reproducible), 9 (tables,
per face) and 10 (the face set) are v0.2's; 11 (features) and 12 (feature
widths), per face, are v0.3's; 13-18 are v0.4's, over Harena UI J, in
scripts/verify_j.py. Any failure, including an error inside a check,
makes the exit status non-zero. The last line is `gate: PASS` or `gate: FAIL`.

The gate does not take its expectations from scripts/build.py. The values the
spec fixes are written here, the Open Sans reference is instanced, decomposed
and stripped of the features Segoe lacks here, and the overlap criterion is
computed here. What it reads from the build is the fonts, and
data/v0_3/build.json (each face's chosen point and glyph copies), whose claims
it checks rather than trusts. It writes each face's
compiled Open Sans reference to build/verify-reference-<face>.ttf for shaping.

Usage: python scripts/verify.py [--no-rebuild]

Without --no-rebuild the gate builds twice and compares the bytes with each
other and with SHA256SUMS as committed at HEAD.
"""
import hashlib
import io
import re
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
from fontTools import unicodedata as fu
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otBase
from fontTools.varLib.instancer import instantiateVariableFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_icons  # noqa: E402
import verify_j  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OPEN_SANS = ROOT / "sources/opensans/OpenSans[wdth,wght].ttf"
TARGET = ROOT / "data/v0_1/segoe-ui-variable.json"
SEGOE = ROOT / "data/v0_2/segoe"
POINTS = ROOT / "data/v0_3/build.json"
FEATURES = ROOT / "data/v0_3/segoe"
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
# PLAN.md v0.3: the features Segoe has, and `liga`; GPOS has kern from Segoe's numbers.
GSUB_FEATURES = {"ccmp", "dlig", "frac", "liga", "tnum"}
GPOS_FEATURES = {"kern", "mark", "mkmk"}


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
        3: f"0.3.0;HRNA;{ps}", 4: f"{family} {style}", 5: "Version 0.3.0", 6: ps,
        13: "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
            "This license is available with a FAQ at: https://openfontlicense.org",
        14: "https://openfontlicense.org", 16: family, 17: style,
    }


FORBIDDEN = ("segoe", "selawik", "source", "pretendard")
# Scope item 2's point: median ink width equal, within rounding wdth to 0.1; and
# the integer wght whose compiled stem is nearest Segoe's. The build searches
# near its solution; the gate searches the whole axis, so it does not depend on
# where the build looked.
INK_RATIO_TOL = 0.005
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


def decomposed(font):
    """Every composite replaced by its outline, as the build does before it
    respaces; otherwise glyphs used only as components would outlive stripping."""
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    gs, glyf = font.getGlyphSet(), font["glyf"]
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
    return font


def strip_features(font):
    """Open Sans as v0.3 specifies it, written here rather than taken from the
    build: only the features Segoe has, and `liga` (GSUB_FEATURES), and mark
    attachment; and only the glyphs the cmap reaches through them."""
    from fontTools import subset
    opts = subset.Options()
    opts.layout_features = sorted(GSUB_FEATURES | {"mark", "mkmk"})
    opts.layout_scripts = ["*"]
    opts.glyph_names = opts.notdef_glyph = opts.notdef_outline = True
    opts.name_IDs, opts.name_languages, opts.name_legacy = ["*"], ["*"], True
    opts.hinting = opts.legacy_kern = opts.symbol_cmap = opts.passthrough_tables = True
    opts.drop_tables = []
    opts.prune_unicode_ranges = opts.prune_codepage_ranges = False
    opts.recalc_bounds = opts.recalc_timestamp = opts.canonical_order = False
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=list(font.getBestCmap()))
    sub.subset(font)
    return font


def nested(subtable):
    """The lookup records of a contextual subtable, of any format."""
    out = list(getattr(subtable, "SubstLookupRecord", None) or getattr(subtable, "PosLookupRecord", None) or [])
    for sets, rules in (("SubRuleSet", "SubRule"), ("SubClassSet", "SubClassRule"),
                        ("ChainSubRuleSet", "ChainSubRule"), ("ChainSubClassSet", "ChainSubClassRule"),
                        ("PosRuleSet", "PosRule"), ("PosClassSet", "PosClassRule"),
                        ("ChainPosRuleSet", "ChainPosRule"), ("ChainPosClassSet", "ChainPosClassRule")):
        for rs in getattr(subtable, sets, None) or []:
            for rule in (getattr(rs, rules, None) or []) if rs else []:
                out += list(getattr(rule, "SubstLookupRecord", None) or getattr(rule, "PosLookupRecord", None) or [])
    return out


def reached(table, tags):
    """Indices of the lookups the features `tags` use, directly or nested."""
    todo = [i for r in table.FeatureList.FeatureRecord if r.FeatureTag in tags
            for i in r.Feature.LookupListIndex]
    seen = set()
    while todo:
        i = todo.pop()
        if i not in seen:
            seen.add(i)
            todo += [rec.LookupListIndex for t in table.LookupList.Lookup[i].SubTable for rec in nested(t)]
    return seen


def drop_lookups(table, drop, tags=()):
    """Remove lookups `drop` and features `tags`, renumbering what is left."""
    keep = [i for i in range(len(table.LookupList.Lookup)) if i not in drop]
    new = {old: n for n, old in enumerate(keep)}
    table.LookupList.Lookup = [table.LookupList.Lookup[i] for i in keep]
    for lookup in table.LookupList.Lookup:
        for t in lookup.SubTable:
            for rec in nested(t):
                rec.LookupListIndex = new[rec.LookupListIndex]
    recs = table.FeatureList.FeatureRecord
    gone = {n for n, r in enumerate(recs) if r.FeatureTag in tags}
    fnew = {old: n for n, old in enumerate(i for i in range(len(recs)) if i not in gone)}
    for r in recs:
        r.Feature.LookupListIndex = [new[i] for i in r.Feature.LookupListIndex if i in new]
    table.FeatureList.FeatureRecord = [r for n, r in enumerate(recs) if n not in gone]
    for sr in table.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
            if ls is not None:
                ls.FeatureIndex = [fnew[i] for i in ls.FeatureIndex if i in fnew]
                if ls.ReqFeatureIndex != 0xFFFF:
                    ls.ReqFeatureIndex = fnew.get(ls.ReqFeatureIndex, 0xFFFF)


def dotless_before():
    """The characters before which Segoe draws `i` dotless, from v0.2's measurements:
    in every face where `ı` is narrower than `i`, `i` before them measures as `ı`."""
    pairs_from = json.loads(TARGET.read_text())["kern_pairs_from"]
    sets = []
    for size, w in FACES:
        seg_ = json.loads((SEGOE / f"{face_key(size, w)}.json").read_text())
        a, k = seg_["advance"], seg_["kern"]
        if abs(a["105"] - a["305"]) >= 0.01:
            sets.append({x for x in pairs_from
                         if abs(a["105"] + k.get(f"105,{x}", 0) - a["305"] - k.get(f"305,{x}", 0)) < 0.05})
    return set.intersection(*sets) if sets else set()


def measured_features(key):
    """A face's measured feature cases, each with Segoe's `width`, and its
    base-and-mark matrix with Segoe's `delta` (data/v0_3)."""
    shared = json.loads((FEATURES.parent / "cases.json").read_text())
    face_ = json.loads((FEATURES / f"{key}.json").read_text())
    return ([{**c, "width": w} for c, w in zip(shared["cases"], face_["widths"], strict=True)],
            {**shared["marks"], "delta": face_["delta"]})


def cgj_letters(cases):
    """The letters a face's Segoe draws narrower before CGJ, which its ccmp reads and
    Open Sans does not map (PLAN.md v0.3), each with how much narrower: coverage,
    from the measurements."""
    widths = {c["text"]: c["width"] for c in cases if c["group"] == "cgj" and not c["css"]}
    return {t[0]: widths[t[0]] - w for t, w in widths.items()
            if len(t) == 2 and t[1] == "\u034F" and abs(w - widths[t[0]]) > 1 / 64}


def own_script(base, mark):
    """Whether a combining mark is written after this letter (PLAN.md v0.3): the
    mark is of the inherited script, or the letter's script is one the mark is used
    with (Unicode Script_Extensions)."""
    return fu.script(mark) == "Zinh" or fu.script(base) in fu.script_extension(mark)


def dotless_marks():
    """The combining marks before which Segoe draws `i` dotless, from v0.3's
    base-and-mark measurements: in every face where `ı` is narrower than `i`, `i`
    and the mark measure as `ı` alone does."""
    sets = []
    for size, w in FACES:
        a = json.loads((SEGOE / f"{face_key(size, w)}.json").read_text())["advance"]
        if abs(a["105"] - a["305"]) < 0.01:
            continue
        m = measured_features(face_key(size, w))[1]
        sets.append({k for k in m["marks"] if own_script("i", k)
                     and abs(m["delta"][""].get("i" + k, 0.0) - (a["305"] - a["105"])) < 0.05})
    return set.intersection(*sets) if sets else set()


def respaced_by_features(font):
    """Glyphs v0.3 respaces that no character maps: the outputs of `frac`'s and
    `ccmp`'s single substitutions; and the combining marks both fonts space, which
    take Segoe's width after a letter. Check 12 holds their widths to Segoe's."""
    gsub = font["GSUB"].table
    cmap = font.getBestCmap()
    mapped = set(cmap.values())
    classes = font["GDEF"].table.GlyphClassDef.classDefs
    target = set(json.loads(TARGET.read_text())["target"])
    spaced = {g for cp, g in cmap.items() if cp not in target
              and unicodedata.category(chr(cp)) in ("Mn", "Me") and classes.get(g) != 3}
    out = set()
    for i in reached(gsub, ("frac", "ccmp")):
        lookup = gsub.LookupList.Lookup[i]
        for t in lookup.SubTable:
            t = t.ExtSubTable if lookup.LookupType == 7 else t
            if getattr(t, "mapping", None):
                out |= set(t.mapping.values())
            for ligs in getattr(t, "ligatures", {}).values():
                out |= {lig.LigGlyph for lig in ligs}
    return (out - mapped) | spaced


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

    tracked = ("SHA256SUMS", "data/v0_3/build.json")
    committed = all(git("cat-file", "-e", f"HEAD:./{p}") == 0 for p in tracked)
    same_as_head = git("diff", "--quiet", "HEAD", "--", *tracked) == 0
    want = "".join(f"{h}  {p.relative_to(ROOT)}\n" for h, p in zip(hashes[0], paths))
    listed = (ROOT / "SHA256SUMS").read_text() == want
    check("8 reproducible", hashes[0] == hashes[1] and committed and same_as_head and listed,
          f"two builds of {len(paths)} faces {'identical' if hashes[0] == hashes[1] else 'differ'}; "
          + ("SHA256SUMS lists them" if listed else "SHA256SUMS does not list exactly these") + "; "
          + ("not committed" if not committed else
             "SHA256SUMS and build.json equal HEAD's" if same_as_head else "differ from HEAD"))


def faces():
    """Check 10: exactly the fifteen files, upright, static, unhinted, with the
    weight and style bits PLAN.md v0.2 gives each. Names are check 6, per face."""
    want = {font_path(*f).name for f in FACES}
    have = {p.name for p in (ROOT / "dist").glob("*") if p.is_file() and not p.name.startswith(("HarenaUIJ-", "HarenaUIIcons-"))}
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
        # nothing beyond the tables a static TrueType UI face needs (no legacy kern, morx, ...)
        extra = set(f.keys()) - {"GlyphOrder", "GDEF", "GPOS", "GSUB", "OS/2", "cmap", "gasp", "glyf",
                                 "head", "hhea", "hmtx", "loca", "maxp", "name", "post"}
        if extra:
            off.append(f"tables {sorted(extra)}")
        # Unhinted, with gasp 0x000A at every size (v0.1, kept by v0.2).
        off += [f"has {t}" for t in ("fpgm", "prep", "cvt ", "cvar", "hdmx", "LTSH", "VDMX") if t in f]
        if "gasp" not in f or f["gasp"].gaspRange != {0xFFFF: 0x000A}:
            off.append("gasp is not {0xFFFF: 0x000A}")
        glyf = f["glyf"]
        hinted = [g for g in f.getGlyphOrder()
                  if hasattr(glyf[g], "program") and glyf[g].program.getBytecode()]
        if hinted:
            off.append(f"glyph programs in {hinted[:4]}")
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


def names_in(x):
    """Every string in a canon() form: glyph names among them."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from names_in(k)
            yield from names_in(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from names_in(v)


def features_and_scripts(table):
    """FeatureList and ScriptList with feature indices resolved to (tag, lookup
    indices), so removing a feature does not renumber the others."""
    recs = table.FeatureList.FeatureRecord
    resolved = [(r.FeatureTag, tuple(r.Feature.LookupListIndex), repr(canon(r.Feature.FeatureParams)))
                for r in recs]
    feats = list(resolved)
    scripts = {}
    for sr in table.ScriptList.ScriptRecord:
        systems = [("dflt", sr.Script.DefaultLangSys)] + [(r.LangSysTag, r.LangSys) for r in sr.Script.LangSysRecord]
        for tag, ls in systems:
            if ls is None:
                continue
            req = ls.ReqFeatureIndex
            scripts[(sr.ScriptTag, tag)] = (
                None if req == 0xFFFF else resolved[req],
                [resolved[i] for i in ls.FeatureIndex])
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
    """Normalise the known edits away and compare. `ref` is Open Sans with the
    features Segoe lacks already stripped (strip_features). On the font's side:
    the kern and dlig features and their lookups are removed; every anchor is
    moved back by its glyph's shift; each copy's GSUB references are renamed to
    its original only where the build puts them (a `.liga` copy as a default
    ligature's output, a `.ccmp` copy as the output of a substitution `ccmp`
    reaches, a `.tnum` copy as `tnum`'s output from its original), and any other
    occurrence fails; its mark records and GDEF class, once shown equal to the
    original's, are dropped. `tnum` itself is removed once it is shown to hold
    nothing but those entries: Open Sans' own `tnum` reads only figures that
    `pnum` reaches, so stripping removes it. On Open Sans' side: the three spacing
    accents leave mark attachment and become base glyphs. Returns a list of
    differences."""
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

    # GSUB: dlig's lookups (with the ones they nest) are appended after Open Sans' own
    # and reached by nothing else; check 11 reads them, and they are set aside here
    n_s = len(gsub.LookupList.Lookup)
    n_ref_s = n_s - len(reached(gsub, ("dlig",)))
    own = len(rgsub.LookupList.Lookup) + len(reached(gsub, ("tnum",)))
    if n_ref_s != own:
        out.append(f"GSUB has {n_ref_s} lookups besides dlig's, not Open Sans' {own} with tnum")
    dlig = [(k, r) for k, r in enumerate(gsub.FeatureList.FeatureRecord) if r.FeatureTag == "dlig"]
    others = {r.FeatureTag for r in gsub.FeatureList.FeatureRecord} - {"dlig"}
    if len(dlig) != 1 or reached(gsub, ("dlig",)) != set(range(n_ref_s, n_s)) \
            or reached(gsub, tuple(others)) & set(range(n_ref_s, n_s)):
        out.append("GSUB dlig is not one feature on all the lookups after Open Sans' own, or "
                   "another feature reaches them")
    else:
        for sr in gsub.ScriptList.ScriptRecord:
            for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
                if ls is not None and dlig[0][0] not in ls.FeatureIndex:
                    out.append(f"dlig is missing from a language system of {sr.ScriptTag}")
        drop_lookups(gsub, set(range(n_ref_s, n_s)), ("dlig",))
    if any(r.FeatureTag == "dlig" for r in rgsub.FeatureList.FeatureRecord):
        out.append("Open Sans has a dlig feature")

    # GSUB: a copy may appear only where the build puts it — a `.liga` copy as the
    # output of a default ligature, a `.tnum` copy as the output of `tnum` — and is
    # renamed back only there. `tnum`'s entry from the original to its copy is the
    # one added; the rest must then be Open Sans'.
    on = {}
    for tag in {r.FeatureTag for r in gsub.FeatureList.FeatureRecord}:
        for i in reached(gsub, (tag,)):
            on.setdefault(i, set()).add(tag)
    misplaced = []
    # only a digit has a tabular copy (check 2t measures them)
    digits = {font.getBestCmap()[c] for c in range(0x30, 0x3A)}
    for i, lookup in enumerate(gsub.LookupList.Lookup):
        tags = on.get(i, set())
        for t in lookup.SubTable:
            if lookup.LookupType == 4:
                for ligs in t.ligatures.values():
                    for lig in ligs:
                        if lig.LigGlyph in copies:
                            if lig.LigGlyph.endswith(".liga") and tags and tags <= {"liga", "clig", "rlig"}:
                                lig.LigGlyph = copies[lig.LigGlyph]
                            elif re.search(r"\.ccmp\d*$", lig.LigGlyph) and tags == {"ccmp"}:
                                lig.LigGlyph = copies[lig.LigGlyph]
                            else:
                                misplaced.append((i, lig.LigGlyph))
            elif lookup.LookupType == 1:
                for k, v in list(t.mapping.items()):
                    if v in copies:
                        if v.endswith(".tnum") and tags == {"tnum"} and k == copies[v] \
                                and k in digits:
                            del t.mapping[k]
                        elif re.search(r"\.ccmp\d*$", v) and tags == {"ccmp"}:
                            t.mapping[k] = copies[v]
                        else:
                            misplaced.append((i, v))
    tnum = reached(gsub, ("tnum",))
    left = [(i, m) for i in tnum for st_ in gsub.LookupList.Lookup[i].SubTable
            for m in getattr(st_, "mapping", {}).items()]
    if left or any(gsub.LookupList.Lookup[i].LookupType != 1 for i in tnum) \
            or any(on[i] != {"tnum"} for i in tnum):
        out.append(f"tnum holds more than each digit to its .tnum copy: {left[:4]}")
    elif any(r.FeatureTag == "tnum" for r in rgsub.FeatureList.FeatureRecord):
        out.append("stripped Open Sans still has a tnum feature")
    else:
        drop_lookups(gsub, tnum, ("tnum",))

    # ccmp: Open Sans' rule making `i` and its kin dotless before marks above looks
    # ahead, in addition, to exactly the characters Segoe draws `i` dotless before:
    # the marks (dotless_marks) and the spacing accents (dotless_before), both derived
    # here from the measurements
    rcmap = ref.getBestCmap()
    extra = {rcmap[c] for c in {ord(k) for k in dotless_marks()} | dotless_before() if c in rcmap}
    for i in reached(gsub, ("ccmp",)):
        if i >= len(rgsub.LookupList.Lookup):
            continue
        for st_, rst in zip(gsub.LookupList.Lookup[i].SubTable, rgsub.LookupList.Lookup[i].SubTable):
            if gsub.LookupList.Lookup[i].LookupType == 6 and st_.Format == 3 and rst.Format == 3 \
                    and len(rst.LookAheadCoverage) == 1 and rcmap[0x69] in rst.InputCoverage[0].glyphs:
                want = set(rst.LookAheadCoverage[0].glyphs) | extra
                if len(st_.LookAheadCoverage) == 1 and set(st_.LookAheadCoverage[0].glyphs) == want:
                    st_.LookAheadCoverage[0].glyphs = list(rst.LookAheadCoverage[0].glyphs)
                else:
                    out.append("ccmp's dotless rule does not look ahead to exactly Open Sans' marks "
                               "and Segoe's dotless characters")

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

    # GPOS: kern is one or two lookups appended after Open Sans' own (pairs, then
    # ligatures' inner kerning), and nothing else reaches them
    n_ref, n = len(rgpos.LookupList.Lookup), len(gpos.LookupList.Lookup)
    kern = [(k, r) for k, r in enumerate(gpos.FeatureList.FeatureRecord) if r.FeatureTag == "kern"]
    if len(kern) != 1 or list(kern[0][1].Feature.LookupListIndex) not in ([n_ref], [n_ref, n_ref + 1]) \
            or n not in (n_ref + 1, n_ref + 2) or reached(gpos, ("mark", "mkmk")) & set(range(n_ref, n)):
        out.append("GPOS kern is not one feature on the one or two lookups after Open Sans' own, "
                   "or another feature reaches them")
    else:
        for sr in gpos.ScriptList.ScriptRecord:
            for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
                if ls is not None and kern[0][0] not in ls.FeatureIndex:
                    out.append(f"kern is missing from a language system of {sr.ScriptTag}")
        drop_lookups(gpos, set(range(n_ref, n)), ("kern",))
    if any(r.FeatureTag == "kern" for r in rgpos.FeatureList.FeatureRecord):
        out.append("Open Sans has a kern feature")
    if features_and_scripts(gpos) != features_and_scripts(rgpos):
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
    """Checks 1-7, 9, 11 and 12 for one face. Returns (lines, failed)."""
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
        ref = compiled(strip_features(decomposed(compiled(instantiateVariableFont(
            TTFont(OPEN_SANS), {"wght": point["wght"], "wdth": point["wdth"]}, updateFontNames=False)))))
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
        # frac's and ccmp's outputs take Segoe's widths for what they stand for
        # (v0.3), which check 12 measures
        by_feature = respaced_by_features(font)
        rest = [g for g in ref.getGlyphOrder() if g not in targets and g not in by_feature]
        others = [g for g in rest if g not in hmtx.metrics or hmtx[g][0] != ref["hmtx"][g][0]]
        check(f"{key} 1 advances", not bad and not others,
              f"{len(target) - len(bad)}/{len(target)} target glyphs at Segoe's advance; "
              f"{len(rest) - len(others)}/{len(rest)} others at Open Sans'; "
              f"{len(by_feature)} frac and ccmp outputs left to check 12"
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
        # be Segoe's for the same characters. Also with ZWNJ between the ligature and
        # the letter, which keeps a longer ligature from forming (`ff` ZWNJ `l` is not
        # `ffl`), so that the pair the ligature has with that letter is shaped too.
        ligs = ligatures(font)
        seq = lambda cps: sum(seg["advance"][str(c)] for c in cps) + sum(
            kern.get(f"{a},{b}", 0.0) for a, b in zip(cps, cps[1:]))
        runs = 0
        for cps in ligs.values():
            text = "".join(map(chr, cps))
            for x in letters:
                for t, cps2 in ((chr(x) + text, [x] + cps), (text + chr(x), cps + [x]),
                                (chr(x) + "\u200c" + text, [x] + cps),
                                (text + "\u200c" + chr(x), cps + [x])):
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
        # each ligature's adjustment for the kerning between its own components
        inner = {}
        for i in idx:
            lookup = gpos.LookupList.Lookup[i]
            for t in lookup.SubTable if lookup.LookupType == 1 else []:
                values = t.Value if t.Format == 2 else [t.Value] * len(t.Coverage.glyphs)
                for g, v in zip(t.Coverage.glyphs, values):
                    inner.setdefault(g, v.XAdvance)  # shaping applies the first
        chars_of = lambda g: ligs[g] if g in ligs else [by_glyph[g]] if g in by_glyph else None
        for i in idx:
            lookup = gpos.LookupList.Lookup[i]
            if lookup.LookupType == 1:
                # The kerning between a ligature's own components (v0.3): its advance
                # is the components' advances, and this brings it to Segoe's kerned
                # width, so that with kern off it is Segoe's unkerned width.
                for t in lookup.SubTable:
                    if t.ValueFormat != 0x0004 or lookup.LookupFlag not in (0, 0x0008):
                        stray.append(("ligature value format", t.ValueFormat, lookup.LookupFlag))
                    values = t.Value if t.Format == 2 else [t.Value] * len(t.Coverage.glyphs)
                    for g, v in zip(t.Coverage.glyphs, values):
                        cps = ligs.get(g)
                        if cps is None:
                            stray.append(("single", g))
                            continue
                        summed = round(sum(seg["advance"][str(c)] for c in cps) * PX)
                        if hmtx[g][0] != summed or abs(summed + v.XAdvance - seq(cps) * PX) > 0.5:
                            stray.append(("ligature", g, hmtx[g][0], v.XAdvance))
                continue
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
                            continue
                        # Every stored value, not only those default shaping reaches (a
                        # longer ligature can hide `ﬀ` + `l`): the pair as stored is as wide
                        # as Segoe's characters, each ligature as its components kerned.
                        ca, cb = chars_of(first), chars_of(rec.SecondGlyph)
                        got = hmtx[first][0] + inner.get(first, 0) + hmtx[rec.SecondGlyph][0] \
                            + inner.get(rec.SecondGlyph, 0) + rec.Value1.XAdvance
                        want = (seq(ca) + seq(cb) + kern[f"{ca[-1]},{cb[0]}"]) * PX
                        if abs(got - want) > 0.5:
                            stray.append(("value", first, rec.SecondGlyph, rec.Value1.XAdvance,
                                          round(want - got + rec.Value1.XAdvance, 1)))
        # `ccmp` draws these letters dotless before these accents, as Segoe's does; with
        # ccmp off Segoe does not kern them (check 12's dotless cases), so neither may this
        gsub_ = font["GSUB"].table
        letters = set()
        for i_ in reached(gsub_, ("ccmp",)):
            for st_ in gsub_.LookupList.Lookup[i_].SubTable:
                if gsub_.LookupList.Lookup[i_].LookupType == 6 and st_.Format == 3 \
                        and len(st_.LookAheadCoverage) == 1 and cmap[0x69] in st_.InputCoverage[0].glyphs:
                    letters |= set(st_.InputCoverage[0].glyphs)
        accent_glyphs = {cmap[c] for c in dotless_before() if c in cmap}
        if cmap[0x69] not in letters:
            stray.append(("ccmp has no dotless rule for i",))
        for i_ in idx:
            lookup = gpos.LookupList.Lookup[i_]
            for t in lookup.SubTable if lookup.LookupType == 2 else []:
                for first, ps in zip(t.Coverage.glyphs, t.PairSet):
                    last = first if first not in ligs else cmap.get(ligs[first][-1])
                    for rec in ps.PairValueRecord:
                        if last in letters and rec.SecondGlyph in accent_glyphs:
                            stray.append(("dotless letter kerned", first, rec.SecondGlyph))
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
        # wght is an integer on Open Sans' axis, and no integer on the axis gives a
        # compiled stem nearer Segoe's (a compiled stem jitters by a unit, so a
        # local check is not enough). Where Segoe's stem is beyond Open Sans'
        # range, the point stops at the axis' end (PLAN.md v0.2, Light).
        axes = {a.axisTag: (a.minValue, a.maxValue) for a in TTFont(OPEN_SANS)["fvar"].axes}
        wmin, wmax = axes["wght"]
        dmin, dmax = axes["wdth"]
        if not isinstance(point["wght"], int) or not wmin <= point["wght"] <= wmax \
                or not dmin <= point["wdth"] <= dmax:
            bad.append(f"point {point['wght']}, {point['wdth']} is not an integer wght and a wdth "
                       "on Open Sans' axes")
        else:
            own = abs(stem - target_stem)
            for nw in range(int(wmin), int(wmax) + 1):
                if abs(l_stem(nw, point["wdth"]) - target_stem) < own - 1e-9:
                    bad.append(f"stem {stem:.2f} px against {target_stem}: wght {nw} is nearer")
                    break
        clamped = (point["wght"] == wmin and stem > target_stem) or \
                  (point["wght"] == wmax and stem < target_stem)
        if ("wght" in point["clamped"]) != clamped:
            bad.append(f"build.json says clamped {point['clamped']}, stem {stem:.2f}/{target_stem}")
        wdth_clamped = (point["wdth"] == dmax and ratio > 1) or (point["wdth"] == dmin and ratio < 1)
        if ("wdth" in point["clamped"]) != wdth_clamped:
            bad.append(f"build.json says clamped {point['clamped']}, ink ratio {ratio:.4f}")
        if abs(ratio - 1) > INK_RATIO_TOL and not wdth_clamped:
            bad.append(f"median ink ratio {ratio:.4f}")
        tables = lambda f: sorted((t.platformID, t.platEncID, t.format, sorted(t.cmap.items()))
                                  for t in f["cmap"].tables)
        if tables(font) != tables(ref):
            bad.append("a cmap subtable differs from Open Sans'")
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

    def c11():
        bad = []
        for tag, allowed in (("GSUB", GSUB_FEATURES), ("GPOS", GPOS_FEATURES)):
            table = font[tag].table
            have = {r.FeatureTag for r in table.FeatureList.FeatureRecord}
            if have != allowed:
                bad.append(f"{tag} features {sorted(have)}")
            if getattr(table, "FeatureVariations", None):
                bad.append(f"{tag} has feature variations")
            recs = table.FeatureList.FeatureRecord
            for sr in table.ScriptList.ScriptRecord:
                for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
                    if ls is None:
                        continue
                    if ls.ReqFeatureIndex != 0xFFFF:
                        bad.append(f"{tag} {sr.ScriptTag} has a required feature")
                    # every language system has every feature once, so no run loses one,
                    # and no second record of a tag can stand in front of the first
                    tags_ = [recs[i].FeatureTag for i in ls.FeatureIndex]
                    if set(tags_) != allowed or len(tags_) != len(set(tags_)):
                        bad.append(f"{tag} {sr.ScriptTag} lacks, adds or repeats features")
            # and each feature does the same in every one: no language has a feature of its
            # own, as none of Segoe's does, so every feature but ccmp resolves to the same
            # lookups everywhere, and ccmp (which Open Sans varies by script) to the same
            # lookups across a script's language systems
            resolve = lambda ls: {recs[i].FeatureTag: frozenset(recs[i].Feature.LookupListIndex)
                                  for i in ls.FeatureIndex}
            first = {}
            for sr in table.ScriptList.ScriptRecord:
                systems = [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]
                script_ccmp = None
                for ls in systems:
                    if ls is None:
                        continue
                    for ftag, lookups in resolve(ls).items():
                        if ftag == "ccmp":
                            script_ccmp = lookups if script_ccmp is None else script_ccmp
                            if lookups != script_ccmp:
                                bad.append(f"{tag} {sr.ScriptTag}: ccmp differs between language systems")
                        elif first.setdefault(ftag, lookups) != lookups:
                            bad.append(f"{tag} {sr.ScriptTag}: {ftag} differs between language systems")
        # dlig is Segoe's (PLAN.md v0.3), rule by rule: a ligature reads characters
        # that join, after NFKC, into one of Segoe's sequences and puts out the
        # presentation form that decomposes to it; a single substitution in dlig
        # itself reads a default ligature of such a sequence and puts out its form; a
        # contextual rule changes a character of a Segoe context, before the glyphs
        # that begin with a character that may follow it, into its `.dlig` copy;
        # nothing else. And no text outside them shapes differently.
        hb_font = hb.Font(hb.Face(hb.Blob.from_file_path(str(FONT))))
        order = font.getGlyphOrder()

        def run(text, features):
            buf = hb.Buffer()
            buf.add_str(text)
            buf.guess_segment_properties()
            hb.shape(hb_font, buf, features)
            return [order[i.codepoint] for i in buf.glyph_infos], sum(p.x_advance for p in buf.glyph_positions)
        inventory = json.loads((ROOT / "data/v0_3/segoe-features.json").read_text())["dlig"]
        seqs = {"".join(map(chr, s)) for s in inventory["sequences"]}
        contexts = [({chr(c) for c in x["input"]}, {chr(c) for c in x["lookahead"]})
                    for x in inventory["contexts"]]
        forms = {}
        for cp_ in cmap:
            nfkc = unicodedata.normalize("NFKC", chr(cp_))
            if len(nfkc) > 1:
                forms.setdefault(nfkc, cmap[cp_])
        ligs = ligatures(font)
        text_of = {g: chr(cp_) for cp_, g in sorted(cmap.items(), reverse=True)}
        text_of.update({g: "".join(map(chr, cps)) for g, cps in ligs.items()})
        nfkc_of = lambda g: unicodedata.normalize("NFKC", text_of.get(g, "\0"))
        exact = lambda g: text_of.get(g, "\0")
        begins = {}
        for g, s in text_of.items():
            begins.setdefault(g, set()).add(s[0])
        for cp_, g in cmap.items():
            begins.setdefault(g, set()).add(chr(cp_))
        follows = lambda chars: {g for g, cs in begins.items() if cs & chars}
        gsub = font["GSUB"].table
        applied = {r.LookupListIndex for i in reached(gsub, ("dlig",))
                   for st_ in gsub.LookupList.Lookup[i].SubTable for r in nested(st_)}
        rule_inputs = {}  # nested lookup -> the glyphs its chain rules apply it to
        for i in reached(gsub, ("dlig",)):
            lookup = gsub.LookupList.Lookup[i]
            if lookup.LookupType not in (1, 4, 6) or lookup.LookupFlag:
                bad.append(f"dlig lookup {i} type {lookup.LookupType} flag {lookup.LookupFlag}")
                continue
            for st_ in lookup.SubTable:
                if lookup.LookupType == 4:
                    for first, ls in st_.ligatures.items():
                        for lig in ls:
                            # the characters as written; NFKC only chooses the form
                            seq_key = "".join(exact(g) for g in [first] + list(lig.Component))
                            if seq_key not in seqs or \
                                    lig.LigGlyph != forms.get(unicodedata.normalize("NFKC", seq_key)):
                                bad.append(f"dlig ligature {[first] + list(lig.Component)} -> {lig.LigGlyph}")
                elif lookup.LookupType == 1 and i not in applied:
                    for a_, b_ in st_.mapping.items():
                        if a_ not in ligs or exact(a_) not in seqs or b_ != forms.get(nfkc_of(a_)):
                            bad.append(f"dlig single {a_} -> {b_}")
                elif lookup.LookupType == 6:
                    if st_.Format != 3 or len(st_.InputCoverage) != 1 or st_.BacktrackCoverage \
                            or len(st_.LookAheadCoverage) != 1:
                        bad.append(f"dlig lookup {i} has a context of another form")
                        continue
                    for g in st_.InputCoverage[0].glyphs:
                        allowed = set().union(*(follows(a) for f_, a in contexts
                                                if any(g == cmap.get(ord(ch)) for ch in f_)), set())
                        if not allowed or not set(st_.LookAheadCoverage[0].glyphs) <= allowed:
                            bad.append(f"dlig rule on {g} in a context Segoe's is not")
                        for r in st_.SubstLookupRecord:
                            rule_inputs.setdefault(r.LookupListIndex, set()).add(g)
        for i, inputs in rule_inputs.items():
            for st_ in gsub.LookupList.Lookup[i].SubTable:
                if gsub.LookupList.Lookup[i].LookupType != 1 or set(st_.mapping) - inputs or any(
                        copies.get(b_) != a_ or not b_.endswith(".dlig") for a_, b_ in st_.mapping.items()):
                    bad.append(f"dlig context lookup {i} maps {dict(list(st_.mapping.items())[:4])}")
        for q in sorted(seqs):
            if all(ord(ch) in cmap for ch in q):
                want = forms.get(unicodedata.normalize("NFKC", q))
                for feats in ({"dlig": True}, {"dlig": True, "liga": False, "clig": False}):
                    if run(q, feats)[0] != [want]:
                        bad.append(f"dlig {q!r} {feats} shapes to {run(q, feats)[0]}, not {want}")
        # outside Segoe's sequences and contexts, dlig changes no glyph and no width: every
        # character alone, and every pair of printable ASCII, dlig characters and spacing
        # accents, with kerning and the default ligatures on and off
        chars = sorted({chr(c) for c in range(32, 127)} | {ch for q in seqs for ch in q}
                       | {ch for f_, a in contexts for ch in f_ | a} | {chr(c) for c in dotless_before()})
        chars = [ch for ch in chars if ord(ch) in cmap]
        moved = [chr(c) for c in cmap if run(chr(c), {}) != run(chr(c), {"dlig": True})]
        # every prefix of a Segoe sequence, and every presentation form, before every character
        heads = {q[:n] for q in seqs for n in range(1, len(q))} | {
            chr(c) for c in cmap if len(unicodedata.normalize("NFKC", chr(c))) > 1}
        for h in sorted(heads):
            for c in cmap:
                text = h + chr(c)
                if any(q in text for q in seqs) or any(text[-2] in f_ and text[-1] in a
                                                       for f_, a in contexts):
                    continue
                for base_ in ({}, {"liga": False, "clig": False}):
                    if run(text, base_) != run(text, {**base_, "dlig": True}) and text not in moved:
                        moved.append(text)
        for base_ in ({}, {"kern": False}, {"liga": False, "clig": False}):
            for x in chars:
                for y in chars:
                    text = x + y
                    if any(q in text for q in seqs) or any(x in f_ and y in a for f_, a in contexts):
                        continue
                    if run(text, base_) != run(text, {**base_, "dlig": True}) and text not in moved:
                        moved.append(text)
        if moved:
            bad.append(f"dlig changes {len(moved)} texts outside Segoe's contexts: {moved[:8]}")
        # every glyph is reachable: stripping again removes nothing
        again = strip_features(compiled(font))
        orphans = sorted(set(font.getGlyphOrder()) - set(again.getGlyphOrder()))
        if orphans:
            bad.append(f"glyphs the cmap does not reach: {orphans[:8]}")
        check(f"{key} 11 features", not bad,
              f"GSUB {sorted(GSUB_FEATURES)}, GPOS {sorted(GPOS_FEATURES)} in every language system; "
              f"dlig is Segoe's sequences and contexts rule by rule, and changes no character and "
              f"no pair of {len(chars)} outside them; "
              f"all {len(font.getGlyphOrder())} glyphs reachable" if not bad else "; ".join(bad))
    guarded(f"{key} 11 features", c11)

    def c12():
        cases12, m = measured_features(key)
        hb_font = hb.Font(hb.Face(hb.Blob.from_file_path(str(FONT))))

        order, seen = font.getGlyphOrder(), set()

        def shaped(text, features=None, lang=""):
            buf = hb.Buffer()
            buf.add_str(text)
            buf.guess_segment_properties()
            if lang:
                buf.language = lang
            hb.shape(hb_font, buf, features or {})
            seen.update(order[i.codepoint] for i in buf.glyph_infos)
            return sum(p.x_advance for p in buf.glyph_positions)

        # Half a unit, plus each kerned pair's own rounding: a font kerns in whole
        # units, and Segoe kerns its Small faces by fractions of one (PLAN.md v0.2
        # item 4), so check 2 holds each such pair within half a unit of Segoe's.
        # Text and Display kern in whole units, so their slack is a few hundredths,
        # where an advance and kern sum to a fraction.
        def tol(text):
            slack = 0.0
            for a, b in zip(text, text[1:]):
                k = seg["kern"].get(f"{ord(a)},{ord(b)}")
                if k:
                    x = (seg["advance"][str(ord(a))] + seg["advance"][str(ord(b))] + k) * PX
                    slack += abs(round(x) - x)
            return 0.5 + slack
        case_tol = lambda c: tol(c["text"])
        bad, n, synthesized, cgj_coverage = [], 0, 0, 0
        before_cgj = cgj_letters(cases12)
        for c in cases12:
            if c["features"] is None:  # the browser synthesizes; item 4 measures it
                synthesized += 1
                continue
            n += 1
            d = shaped(c["text"], c["features"], c["lang"]) - c["width"] * PX
            if abs(d) > case_tol(c):
                # with ccmp on, and by exactly what Segoe's ccmp takes off those letters
                narrower = sum(v * c["text"].count(x + "\u034F") for x, v in before_cgj.items())
                if c["group"] == "cgj" and narrower and (c["features"] or {}).get("ccmp") != 0 \
                        and abs(d - narrower * PX) <= case_tol(c):
                    cgj_coverage += 1
                    continue
                bad.append(f"{c['group']} {c['text']!r} {c['css'] or c['lang']} {d:+.1f}")
        # Base and mark: Harena UI's width change against Segoe's, for each mark after
        # the letters of its script (own_script). A sequence that composes into a
        # character Segoe maps and Harena UI does not is coverage (PLAN.md v0.3),
        # counted and left out.
        segoe_cmap = set(doc["segoe_cmap"])
        coverage, pairs = 0, 0
        for lang in m["langs"]:
            delta = m["delta"][lang]
            for base in m["bases"]:
                wb = shaped(base, lang=lang)
                for mark in m["marks"]:
                    if not own_script(base, mark):
                        continue
                    text = base + mark
                    d = shaped(text, lang=lang) - wb - delta.get(text, 0.0) * PX
                    if abs(d) <= tol(text):
                        pairs += 1
                    elif any(ord(ch) in segoe_cmap and ord(ch) not in cmap
                             for ch in unicodedata.normalize("NFC", text)):
                        coverage += 1
                    else:
                        bad.append(f"mark {lang or '-'} {text!r} {d:+.1f}")
        # Every ligature ccmp forms is among the cases, with a joiner between its
        # characters: composition hides most of them from plain text
        joined = {c["text"] for c in cases12 if c["group"] == "joiner" and not c["css"]}
        chars = {}
        for cp, g in sorted(cmap.items()):
            chars.setdefault(g, cp)
        gsub = font["GSUB"].table
        for i in reached(gsub, ("ccmp",)):
            for st_ in gsub.LookupList.Lookup[i].SubTable:
                for first, ligs in getattr(st_, "ligatures", {}).items():
                    for lig in ligs:
                        comps = [first, *lig.Component]
                        if not all(g in chars and chars[g] in segoe_cmap for g in comps):
                            continue
                        text = "\u200D".join(chr(chars[g]) for g in comps)
                        if text not in joined:
                            bad.append(f"ccmp ligature {lig.LigGlyph} not measured")
        # every glyph check 1 leaves to this check has been measured here
        # and so has every glyph this build added, whatever made it
        unshaped = sorted((respaced_by_features(font) | set(copies)) - seen)
        if unshaped:
            bad.append(f"respaced glyphs no case reaches: {unshaped[:8]}")
        check(f"{key} 12 feature widths", not bad,
              f"{n} cases and {pairs} base+mark pairs within half a unit of Segoe's (plus "
              f"fractional kerning's rounding); {synthesized} "
              f"synthesized cases left to the browser; {coverage} coverage pairs and "
              f"{cgj_coverage} cases before CGJ left out"
              + (f"; off ({len(bad)}): {bad[:8]}" if bad else ""))
    guarded(f"{key} 12 feature widths", c12)
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
    if "--no-rebuild" in sys.argv:
        print("SKIP J 18 reproducible: --no-rebuild", flush=True)
    else:
        out, bad = verify_j.reproducible_j()
        print("\n".join(out), flush=True)
        failed.extend(bad)
    with ProcessPoolExecutor() as pool:
        for out, bad in pool.map(verify_j.face_j, *zip(*FACES)):
            print("\n".join(out), flush=True)
            failed.extend(bad)
    for name, ok, detail in verify_icons.checks():
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail and not ok else ""), flush=True)
        if not ok:
            failed.append(name)
    print("gate:", "FAIL" if failed else "PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
