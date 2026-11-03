# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Build Harena UI J: each built Harena UI face plus Pretendard JP's CJK, at the widths
Edge gives CJK under a Segoe stack (PLAN.md, v0.4).

Harena UI's glyphs, advances, kerning and vertical metrics are not rebuilt: the face is
loaded from dist/ and CJK is added to it. So scripts/build.py must have run first.

Writes dist/HarenaUIJ-<Size><Weight>.ttf and SHA256SUMS-J, and data/v0_4/build.json, the
weights and scale each face chose, which the gate checks rather than trusts.

Usage: python scripts/build_j.py
"""
import hashlib
import json
import statistics as st
import sys
import unicodedata
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from fontTools import subset, unicodedata as fu
from fontTools.misc.roundTools import otRound
from fontTools.misc.timeTools import timestampSinceEpoch
from fontTools.otlLib import builder as otl
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib.tables._g_l_y_f import flagOverlapSimple
from fontTools.varLib.instancer import instantiateVariableFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import COPYRIGHT, DIST, FACES, LICENSE, ROOT, SOURCE_DATE, UPM, VENDOR, WEIGHTS, face_name, face_path  # noqa: E402

PJP = ROOT / "sources/pjp/public/variable/PretendardJPVariable.ttf"
DATA = ROOT / "data/v0_4"
WORK = ROOT / "build/j"
VERSION = "0.6.0"
COPYRIGHT_J = (COPYRIGHT + "\nCopyright (c) 2021, Kil Hyung-jin (https://github.com/orioncactus/pretendard), "
               "with Reserved Font Name Pretendard JP")
PX = UPM / 1000
# Measured language -> OpenType language system
SYSTEMS = {"": None, "ko": "KOR ", "ja": "JAN ", "zh-Hans": "ZHS ", "zh-Hant": "ZHT "}
# The scripts a run of CJK or of its neighbours shapes under. Harena UI's have its own
# systems; the others take DFLT's features.
CJK_SCRIPTS = {"hang": "hangul", "hani": "han", "kana": None}
MARKS = (0x3099, 0x309A)
# Half a width alone and 1 em beside anything, with no `lang`: what they are beside
# anything is what they get (PLAN.md).
ALONE_ODD = (0xFF5F, 0xFF60)
# Halved at the leading edge, by `halt` and by a narrower width: their ink is at the trailing
# edge. Others of a width change keep their ink at the leading edge (closing, `、。，．`) or
# centred.
TRAILING_DOTS = (0x3001, 0x3002, 0xFF0C, 0xFF0E)


def category(c):
    return unicodedata.category(chr(c))


def units(px):
    return otRound(px * PX)


def expand(runs):
    return {c: w for first, last, w in runs for c in range(first, last + 1)}


def is_hangul(c):
    return fu.script(chr(c)) == "Hang"


def in_script(c, script):
    """Whether a code point can be in a run of that script: its own letters and the symbols
    that join any run."""
    return fu.script(chr(c)) in {"hang": ("Hang", "Zyyy", "Zinh"), "hani": ("Hani", "Zyyy", "Zinh"),
                                 "kana": ("Hira", "Kana", "Zyyy", "Zinh")}[script]


def windows(size, w):
    return json.loads((DATA / "windows" / f"{size}-{WEIGHTS[w]}.json").read_text())["langs"]


class Targets:
    """What a face's CJK measures, in font units, from what Windows measured."""

    def __init__(self, size, w, cases):
        data, text = windows(size, w), windows("Text", w)
        self.covered, self.symbols = cases["covered"], set(cases["symbols"])
        kana = self.kana = set(cases["kana"])
        self.punctuation = set(cases["punctuation"])
        self.alone = {lang: expand(data[lang]["alone"]) for lang in SYSTEMS}
        # A symbol's width beside Han is its default; everything else's is its width alone.
        self.default = {c: units(self.in_run(data, "", "han", c)) for c in self.covered}
        self.dist, self.kern = {}, {}
        for lang, tag in SYSTEMS.items():
            pairs = text[lang]["kern"]
            run_shift = self._kana_run_shift(pairs, kana)
            for script, name in CJK_SCRIPTS.items():
                table = {}
                for c in self.covered:
                    if c in MARKS or not in_script(c, script):
                        continue
                    if name:
                        px = self.in_run(data, lang, name, c)
                    else:
                        px = self.alone[lang][c] + run_shift.get(c, 0) if c in self.symbols else self.alone[lang][c]
                        if c in ALONE_ODD:
                            px = self.in_run(data, lang, "han", c)
                    if units(px) != self.default[c]:
                        table[c] = units(px) - self.default[c]
                self.dist[script, tag] = table
            table = {}
            for c in self.covered:
                if c in MARKS:
                    continue
                px = self.in_run(data, lang, "han", c) if c in ALONE_ODD else self.alone[lang][c]
                if units(px) != self.default[c]:
                    table[c] = units(px) - self.default[c]
            self.dist["DFLT", tag] = table
            kern = {}
            for text_pair, d in pairs.items():
                a, b = map(ord, text_pair)
                if a in MARKS or b in MARKS:
                    continue
                shift = run_shift.get(a if a in self.symbols else b, 0)
                # Kerning narrows. A wider pair is a kana the language's font lacks, whose font
                # draws the symbol beside it, which no pair can stand for: `ゔ｟ゔ` would count twice.
                if units(d - shift) < 0:
                    kern[a, b] = units(d - shift)
            self.kern[tag] = kern
        # Yu Gothic's half widths, which Edge's text-spacing-trim reads: under Japanese, and in a
        # kana run with no language, which Yu Gothic draws as well.
        self.halt = {int(k): v for k, v in data["ja"]["halt"].items()}

    @staticmethod
    def _after(data, lang, name, c):
        return data[lang]["beside"][name]["after"].get(str(c), 0)

    def in_run(self, data, lang, name, c):
        """A code point's width in a run of that script. A symbol that follows a letter takes
        the run's font; letters of other scripts are themselves in any run."""
        px = self.alone[lang][c]
        return px + self._after(data, lang, name, c) if c in self.symbols else px

    def _kana_run_shift(self, pairs, kana):
        """The most usual change a symbol shows after kana is its width in a kana run; what
        differs from that in a pair is kerning."""
        shift = {}
        for s in self.symbols - set(MARKS):
            seen = Counter(round(pairs.get(chr(a) + chr(s), 0), 3) for a in kana)
            if seen.most_common(1)[0][0]:
                shift[s] = seen.most_common(1)[0][0]
        return shift


def source_subset(covered):
    """Pretendard JP's covered glyphs, without layout, for instancing."""
    font = TTFont(PJP)
    options = subset.Options(layout_features=[], name_IDs=[], notdef_outline=True, glyph_names=True,
                             hinting=False, retain_gids=False, drop_tables=subset.Options().drop_tables + ["GSUB", "GPOS", "GDEF"])
    sub = subset.Subsetter(options)
    sub.populate(unicodes=covered)
    sub.subset(font)
    WORK.mkdir(parents=True, exist_ok=True)
    font.save(WORK / "pjp-subset.ttf")


def instance(wght):
    path = WORK / f"pjp-{wght}.ttf"
    font = instantiateVariableFont(TTFont(WORK / "pjp-subset.ttf"), {"wght": wght}, inplace=True, overlap=False)
    font.save(path)
    return wght


def interpolate(scan, value):
    for (a, va), (b, vb) in zip(scan, scan[1:]):
        if va <= value <= vb and vb > va:
            return a + (b - a) * (value - va) / (vb - va)
    raise ValueError(f"stem {value} is outside Pretendard JP's")


def choose(shapes):
    """Per weight: the wght whose stems meet Malgun Gothic's `ㅣ` once scaled, and Yu Gothic's
    `十`; and the Hangul scale, from the bodies. Scale and stem depend on each other through
    the weight's body only slightly, so 1.08 starts one correction."""
    stems = shapes["stems"]
    scan = sorted((int(k.split("|")[1]), v) for k, v in stems.items() if k.startswith("Pretendard JP Probe|"))
    ko = [ord(c) for c in shapes["ink_sample"]["ko"]]
    chosen = {}
    for w in WEIGHTS:
        malgun = stems[f"Malgun Gothic|{w}"]["ㅣ"]
        yu = stems[f"Yu Gothic|{w}"]["十"]
        han = otRound(interpolate([(a, v["十"]) for a, v in scan], yu))
        ink = shapes["ink"][f"Malgun Gothic|{w}"]
        target = st.median(ink[str(c)][2] - ink[str(c)][3] for c in ko)
        scale = 1.08
        for _ in range(2):
            hangul = otRound(interpolate([(a, v["ㅣ"]) for a, v in scan], malgun / scale))
            sample = instantiateVariableFont(TTFont(WORK / "pjp-subset.ttf"), {"wght": hangul}, inplace=True, overlap=False)
            gs, cmap = sample.getGlyphSet(), sample.getBestCmap()
            heights = []
            for c in ko:
                pen = BoundsPen(gs)
                gs[cmap[c]].draw(pen)
                heights.append(pen.bounds[3] - pen.bounds[1])
            scale = round(target / (st.median(heights) / PX), 3)
        hangul = otRound(interpolate([(a, v["ㅣ"]) for a, v in scan], malgun / scale))
        chosen[w] = {"hangul_wght": hangul, "han_wght": han, "hangul_scale": scale}
    return chosen


def offset(c, advance, source_advance):
    """How far right of its source position a glyph goes in an advance. Opening punctuation keeps
    its trailing bearing and closing its leading one, which is what halving them relies on;
    everything else keeps its source's balance."""
    kind = category(c)
    if kind in ("Ps", "Pi"):
        return advance - source_advance
    if kind in ("Pe", "Pf") or c in TRAILING_DOTS:
        return 0
    return (advance - source_advance) / 2


def glyph_name(c):
    return f"uni{c:04X}" if c < 0x10000 else f"u{c:05X}"


def draw(source, name, scale, dx):
    recording = DecomposingRecordingPen(source)
    source[name].draw(recording)
    pen = TTGlyphPen(None)
    recording.replay(TransformPen(pen, (scale, 0, 0, scale, dx, 0)))
    glyph = pen.glyph(dropImpliedOnCurves=False)
    if glyph.numberOfContours > 0:
        glyph.coordinates.toInt()
        glyph.flags[0] |= flagOverlapSimple
    return glyph


def add_cjk(font, targets, chosen):
    hangul = TTFont(WORK / f"pjp-{chosen['hangul_wght']}.ttf")
    han = TTFont(WORK / f"pjp-{chosen['han_wght']}.ttf")
    scale = chosen["hangul_scale"]
    sources = {True: (hangul, hangul.getGlyphSet(), hangul.getBestCmap(), scale),
               False: (han, han.getGlyphSet(), han.getBestCmap(), 1.0)}
    order = list(font.getGlyphOrder())
    glyf, hmtx = font["glyf"], font["hmtx"]
    names = {}
    added = []
    for c in targets.covered:
        src, gs, cmap, s = sources[is_hangul(c)]
        advance = 0 if c in MARKS else targets.default[c]
        source_advance = src["hmtx"][cmap[c]][0] * s
        # U+3099 and U+309A hang back over the letter before, whose middle moved back by half
        # what it grew
        dx = -(UPM - src["hmtx"][cmap[0x3042]][0]) / 2 if c in MARKS else offset(c, advance, source_advance)
        name = glyph_name(c)
        assert name not in glyf.glyphs, f"{name} is already in Harena UI"
        glyf[name] = draw(gs, cmap[c], s, dx)
        glyph = glyf[name]
        glyph.recalcBounds(glyf)
        hmtx[name] = (advance, glyph.xMin if glyph.numberOfContours else 0)
        names[c] = name
        added.append(name)
    font.setGlyphOrder(order + added)
    glyf.setGlyphOrder(font.getGlyphOrder())
    return names


def set_cmap(font, names):
    cmap = dict(font.getBestCmap())
    cmap.update(names)
    tables = []
    bmp = {c: g for c, g in cmap.items() if c < 0x10000}
    for platform, encoding, fmt, chars in ((0, 3, 4, bmp), (3, 1, 4, bmp), (0, 4, 12, cmap), (3, 10, 12, cmap)):
        table = CmapSubtable.newSubtable(fmt)
        table.platformID, table.platEncID, table.language, table.cmap = platform, encoding, 0, dict(chars)
        tables.append(table)
    font["cmap"].tables = tables


def mark_class(font, names):
    defs = font["GDEF"].table.GlyphClassDef.classDefs
    for c in MARKS:
        defs[names[c]] = 3


def value(c, d):
    """A width change of `d` units at the edge that does not move the ink: see offset()."""
    kind = category(c)
    if kind in ("Ps", "Pi"):
        return otl.buildValue({"XPlacement": d, "XAdvance": d})
    if kind in ("Pe", "Pf") or c in TRAILING_DOTS:
        return otl.buildValue({"XAdvance": d})
    return otl.buildValue({"XPlacement": d // 2, "XAdvance": d})


class Gpos:
    """Adds lookups, features and language systems to Harena UI's GPOS."""

    def __init__(self, font):
        self.font, self.table = font, font["GPOS"].table
        self.glyph_map = font.getReverseGlyphMap()
        self.lookups = {}

    def lookup(self, key, build, flags=0):
        if key not in self.lookups:
            lookup = otl.buildLookup(build(), flags=flags, table=None)
            self.table.LookupList.Lookup.append(lookup)
            self.table.LookupList.LookupCount = len(self.table.LookupList.Lookup)
            self.lookups[key] = len(self.table.LookupList.Lookup) - 1
        return self.lookups[key]

    def single(self, table, names):
        if not table:
            return []
        key = ("single", tuple(sorted(table.items())))
        return [self.lookup(key, lambda: otl.buildSinglePos(
            {names[c]: value(c, d) for c, d in sorted(table.items())}, self.glyph_map))]

    def halve(self, table, names):
        if not table:
            return []
        key = ("halt", tuple(sorted(table)))
        return [self.lookup(key, lambda: otl.buildSinglePos(
            {names[c]: value(c, units(d)) for c, d in sorted(table.items())}, self.glyph_map))]

    def halve_after_kana(self, table, names, kana, punctuation):
        """`halt` that needs kana before the glyph, with up to two punctuation marks between, past
        any combining mark. A kana
        run can start at punctuation (`ア（F）、`: Chromium gives the closing bracket its opening
        bracket's script), and there Windows' fallback takes a font that does not trim."""
        inner = self.halve(table, names)[0]

        def cover(codes):
            return otl.buildCoverage([names[c] for c in codes], self.glyph_map)

        def subtable(between):
            st = ot.ChainContextPos()
            st.Format = 3
            st.BacktrackCoverage = [cover(punctuation) for _ in range(between)] + [cover(kana)]
            st.BacktrackGlyphCount = len(st.BacktrackCoverage)
            st.InputCoverage = [cover(table)]
            st.InputGlyphCount = 1
            st.LookAheadCoverage = []
            st.LookAheadGlyphCount = 0
            record = ot.PosLookupRecord()
            record.SequenceIndex, record.LookupListIndex = 0, inner
            st.PosLookupRecord = [record]
            st.PosCount = 1
            return st

        return [self.lookup(("halt after kana", tuple(sorted(table))), lambda: [subtable(n) for n in range(3)],
                            flags=otl.LOOKUP_FLAG_IGNORE_MARKS)]

    def pairs(self, table, names):
        if not table:
            return []
        key = ("kern", tuple(sorted(table.items())))
        return [self.lookup(key, lambda: otl.buildPairPosGlyphs(
            {(names[a], names[b]): (otl.buildValue({"XAdvance": d}), None) for (a, b), d in sorted(table.items())},
            self.glyph_map))]


def rebuild_systems(font, targets, names):
    gpos = Gpos(font)
    table = gpos.table
    existing = {r.ScriptTag: r.Script for r in table.ScriptList.ScriptRecord}
    records = table.FeatureList.FeatureRecord
    base_features = {tag: [(records[i].FeatureTag, list(records[i].Feature.LookupListIndex))
                           for i in script.DefaultLangSys.FeatureIndex] for tag, script in existing.items()}
    systems = {}
    for script in sorted(set(existing) | set(CJK_SCRIPTS)):
        for lang, tag in SYSTEMS.items():
            base = base_features.get(script, base_features["DFLT"])
            features = [(t, list(lookups)) for t, lookups in base]
            own = script if script in CJK_SCRIPTS else "DFLT"
            extra = gpos.single(targets.dist[own, tag], names)
            if extra:
                features.append(("dist", extra))
            if tag == "JAN ":
                halved = gpos.halve(targets.halt, names)
            elif script == "kana" and tag is None:
                halved = gpos.halve_after_kana(targets.halt, names, targets.kana, targets.punctuation)
            else:
                halved = []
            if halved:
                features.append(("halt", halved))
            if script == "kana":
                more = gpos.pairs(targets.kern[tag], names)
                features = [(t, lookups + more if t == "kern" else lookups) for t, lookups in features]
            systems[script, tag] = features
    # one FeatureRecord per distinct (tag, lookups), in tag order
    distinct = sorted({(t, tuple(lookups)) for features in systems.values() for t, lookups in features})
    index = {key: i for i, key in enumerate(distinct)}
    new_records = []
    for t, lookups in distinct:
        feature = ot.Feature()
        feature.FeatureParams = None
        feature.LookupListIndex = list(lookups)
        feature.LookupCount = len(lookups)
        record = ot.FeatureRecord()
        record.FeatureTag = t
        record.Feature = feature
        new_records.append(record)
    table.FeatureList.FeatureRecord = new_records
    table.FeatureList.FeatureCount = len(new_records)

    def langsys(features):
        ls = ot.LangSys()
        ls.LookupOrder = None
        ls.ReqFeatureIndex = 0xFFFF
        ls.FeatureIndex = sorted(index[t, tuple(lookups)] for t, lookups in features)
        ls.FeatureCount = len(ls.FeatureIndex)
        return ls

    scripts = []
    for script in sorted(set(existing) | set(CJK_SCRIPTS)):
        s = ot.Script()
        s.DefaultLangSys = langsys(systems[script, None])
        s.LangSysRecord = []
        for tag in sorted(t for t in SYSTEMS.values() if t):
            record = ot.LangSysRecord()
            record.LangSysTag = tag
            record.LangSys = langsys(systems[script, tag])
            s.LangSysRecord.append(record)
        s.LangSysCount = len(s.LangSysRecord)
        record = ot.ScriptRecord()
        record.ScriptTag = script
        record.Script = s
        scripts.append(record)
    table.ScriptList.ScriptRecord = scripts
    table.ScriptList.ScriptCount = len(scripts)


def face_path_j(size, w):
    return DIST / f"HarenaUIJ-{size}{WEIGHTS[w]}.ttf"


def names_j(size, w):
    family, style = f"Harena UI J {size}", WEIGHTS[w]
    ribbi = style in ("Regular", "Bold")
    ps = f"HarenaUIJ{size}-{style}"
    return {0: COPYRIGHT_J,
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


def finish(font, size, w):
    os2 = font["OS/2"]
    os2.recalcUnicodeRanges(font)
    os2.recalcCodePageRanges(font)
    # Harena Term's ADR 0012: the Han is Japanese's, so Chinese code pages would invite text it
    # cannot set
    os2.ulCodePageRange1 &= ~((1 << 18) | (1 << 20))
    os2.recalcAvgCharWidth(font)
    name = font["name"]
    name.names = []
    for nid, text in names_j(size, w).items():
        name.setName(text, nid, 3, 1, 0x409)
    font["head"].fontRevision = float(VERSION.rsplit(".", 1)[0])
    font["head"].created = font["head"].modified = timestampSinceEpoch(SOURCE_DATE)
    font.recalcTimestamp = False


def build_face(args):
    size, w, chosen, cases = args
    font = TTFont(face_path(size, w))
    targets = Targets(size, w, cases)
    names = add_cjk(font, targets, chosen)
    set_cmap(font, names)
    mark_class(font, names)
    rebuild_systems(font, targets, names)
    finish(font, size, w)
    font.save(face_path_j(size, w))
    return face_name(size, w)


def build():
    cases = json.loads((DATA / "cases.json").read_text())
    shapes = json.loads((DATA / "shapes.json").read_text())
    source_subset(cases["covered"])
    chosen = choose(shapes)
    wanted = sorted({c[k] for c in chosen.values() for k in ("hangul_wght", "han_wght")})
    with ProcessPoolExecutor() as pool:
        list(pool.map(instance, wanted))
        done = list(pool.map(build_face, [(size, w, chosen[w], cases) for size, w in FACES]))
    (DATA / "build.json").write_text(json.dumps(
        {str(w): c for w, c in chosen.items()}, indent=1, sort_keys=True) + "\n")
    (ROOT / "SHA256SUMS-J").write_text("".join(
        f"{hashlib.sha256(face_path_j(*f).read_bytes()).hexdigest()}  {face_path_j(*f).relative_to(ROOT)}\n"
        for f in FACES))
    print(" ".join(done))
    print(json.dumps(chosen))


if __name__ == "__main__":
    build()
