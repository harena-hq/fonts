# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""The gate's checks over Harena UI J, v0.4: 13 Latin identity, 14 coverage, 15 CJK widths,
16 features and 17 shapes, per face; 18 reproducible, once. Run by scripts/verify.py after
Harena UI's checks.

Like verify.py, this takes no expectation from the build. It reads the fonts, what Windows
measured (data/v0_4), and data/v0_4/build.json, whose claims it checks. It instances Pretendard
JP itself for check 17.

HarfBuzz does not do what Edge's text-spacing-trim does, or split text into runs: run_width()
below splits text the way Chromium's ScriptRunIterator does, and a pair Windows trims is checked
against `halt` on either of its characters. The browser check (probe/v0_4/browser.py) is what
shows Edge does the rest.

Usage: python scripts/verify_j.py [Size-Weight ...]
"""
import hashlib
import io
import json
import statistics as st
import subprocess
import sys
from collections import Counter
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset, unicodedata as fu
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.misc.roundTools import otRound
from fontTools.misc.xmlWriter import XMLWriter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/v0_4"
PJP = ROOT / "sources/pjp/public/variable/PretendardJPVariable.ttf"
SIZES = ("Small", "Text", "Display")
WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
FACES = [(size, w) for size in SIZES for w in WEIGHTS]
UPM = 2048
PX = UPM / 1000
SYSTEMS = {"": None, "ko": "KOR ", "ja": "JAN ", "zh-Hans": "ZHS ", "zh-Hant": "ZHT "}
HB_LANG = {"": "en", "ko": "ko", "ja": "ja", "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant"}
TOLERANCE = 0.5 + 1e-6  # font units
MARKS = (0x3099, 0x309A)
ALONE_ODD = (0xFF5F, 0xFF60)
HANGUL_STEM = "ㅣ"
HAN_STEM = "十"
STEM_ROW_PX = 650
STEM_TOLERANCE = 0.03
BODY_TOLERANCE = 0.02
# Rounded in the build after scaling and moving, and instanced here unrounded
OUTLINE_TOLERANCE = 1.5
# Unicode's paired brackets, which is what Chromium's iterator reads
OPEN = "([{〈《「『【〔〖〘〚（［｛｟"
CLOSE = ")]}〉》」』】〕〗〙〛）］｝｠"


def face_path(size, w):
    return ROOT / "dist" / f"HarenaUI-{size}{WEIGHTS[w]}.ttf"


def j_path(size, w):
    return ROOT / "dist" / f"HarenaUIJ-{size}{WEIGHTS[w]}.ttf"


def expand(runs):
    return {c: v for first, last, v in runs for c in range(first, last + 1)}


def windows(size, w):
    return json.loads((DATA / "windows" / f"{size}-{WEIGHTS[w]}.json").read_text())["langs"]


class Face:
    def __init__(self, path):
        self.font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))

    def shape(self, text, lang, script, features=None):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.direction = "ltr"
        buf.script = script
        buf.language = HB_LANG[lang]
        hb.shape(self.font, buf, features or {})
        return buf

    def width(self, text, lang, script, features=None):
        return sum(p.x_advance for p in self.shape(text, lang, script, features).glyph_positions)

    def run_width(self, text, lang, features=None):
        return sum(self.width(t, lang, s, features) for t, s in runs_of(text))


def runs_of(text):
    """Text split as Chromium's ScriptRunIterator splits it: Common and Inherited characters join
    the run before them, or at the start the run after; a closing bracket joins its opening
    bracket's. A character with script extensions narrows the run's candidates, or starts a run
    if none is left: `ー` after Hangul starts a kana run. Hiragana and Katakana are one run."""
    def candidates(c):
        return {"Kana" if s == "Hira" else s for s in fu.script_extension(c)}

    runs = []  # [text, candidates], where an empty set is Common so far
    stack = []  # [opening bracket, its run], so that what later resolves the run resolves it too
    for c in text:
        have = candidates(c)
        common = have <= {"Zyyy", "Zinh"}
        if c in CLOSE and any(OPEN[CLOSE.index(c)] == o for o, _ in stack):
            while True:
                opener, run = stack.pop()
                if opener == OPEN[CLOSE.index(c)]:
                    break
            have = set(run[1])
            common = not have
        if runs and common:
            runs[-1][0] += c
        elif runs and not runs[-1][1]:
            runs[-1][0] += c
            runs[-1][1] = set(have)
        elif runs and runs[-1][1] & have:
            runs[-1][0] += c
            runs[-1][1] &= have
        else:
            if runs:
                # A run that has ended is resolved, for a closing bracket that reads it later
                runs[-1][1] = {_resolved(runs[-1][1])}
            runs.append([c, set() if common else set(have)])
        if c in OPEN:
            stack.append((c, runs[-1]))
    return [(t, _resolved(s)) for t, s in runs]


def _resolved(candidates):
    """A run still open to several scripts has met only symbols: a run of no script of ours."""
    return next(iter(candidates)) if len(candidates) == 1 else "Zyyy"


def own_script(c):
    s = fu.script(chr(c))
    return "Zyyy" if s in ("Zyyy", "Zinh") else s


def outline(font, gs, name, scale=1.0):
    pen = DecomposingRecordingPen(gs)
    gs[name].draw(pen)
    # A contour's last point on its first is the same outline: the build's pen drops it
    points, ops = [], []
    start = None
    for op, args in pen.value:
        if op == "moveTo":
            start = len(points)
        if op == "closePath" and ops[-1] == "lineTo" and all(
                otRound(a) == otRound(b) for a, b in zip(points[-1], points[start])):
            points.pop()
            ops.pop()
        for x, y in args:
            points.append((x, y))
        ops.append(op)
    return [(x * scale, y * scale) for x, y in points], ops


def row_coverage(font, name, y):
    """The width a glyph's fill covers along the row y, nonzero winding, curves flattened."""
    pen = DecomposingRecordingPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    crossings = []
    start = last = None

    def line(a, b):
        if (a[1] <= y) != (b[1] <= y):
            x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            crossings.append((x, 1 if b[1] > a[1] else -1))

    for op, args in pen.value:
        if op == "moveTo":
            start = last = args[0]
        elif op == "lineTo":
            line(last, args[0])
            last = args[0]
        elif op == "qCurveTo":
            pts = list(args)
            implied = []
            for i, p in enumerate(pts[:-1]):
                nxt = pts[i + 1]
                end = nxt if i == len(pts) - 2 else ((p[0] + nxt[0]) / 2, (p[1] + nxt[1]) / 2)
                implied.append((p, end))
            for ctrl, end in implied:
                prev = last
                for k in range(1, 33):
                    t = k / 32
                    q = ((1 - t) ** 2 * prev[0] + 2 * t * (1 - t) * ctrl[0] + t * t * end[0],
                         (1 - t) ** 2 * prev[1] + 2 * t * (1 - t) * ctrl[1] + t * t * end[1])
                    line(last, q)
                    last = q
        elif op in ("closePath", "endPath"):
            if last != start:
                line(last, start)
            last = start
    crossings.sort()
    total, wind, entered = 0, 0, None
    for x, d in crossings:
        if wind == 0:
            entered = x
        wind += d
        if wind == 0:
            total += x - entered
    return total


class Report:
    def __init__(self, prefix):
        self.prefix, self.lines, self.failed = prefix, [], []

    def check(self, name, ok, detail=""):
        self.lines.append(f"{'PASS' if ok else 'FAIL'} {self.prefix} {name}" + (f": {detail}" if detail else ""))
        if not ok:
            self.failed.append(f"{self.prefix} {name}")

    def guarded(self, name, fn):
        try:
            fn()
        except Exception as e:  # a check that cannot run has failed
            self.check(name, False, f"error: {e!r}")


def table_bytes(font, tag):
    return font[tag].compile(font)


def check_latin(r, j, base, face_j, face_h):
    order_h = base.getGlyphOrder()
    order_j = j.getGlyphOrder()
    same_order = order_j[:len(order_h)] == order_h
    glyf_j, glyf_h, hmtx_j, hmtx_h = j["glyf"], base["glyf"], j["hmtx"], base["hmtx"]
    outlines = [g for g in order_h if glyf_j[g].compile(glyf_j) != glyf_h[g].compile(glyf_h)]
    advances = [g for g in order_h if hmtx_j[g] != hmtx_h[g]]
    cmap_j, cmap_h = j.getBestCmap(), base.getBestCmap()
    remap = [c for c, g in cmap_h.items() if cmap_j.get(c) != g]
    vertical = all(getattr(j["hhea"], k) == getattr(base["hhea"], k) for k in ("ascent", "descent", "lineGap")) and all(
        getattr(j["OS/2"], k) == getattr(base["OS/2"], k)
        for k in ("sTypoAscender", "sTypoDescender", "sTypoLineGap", "usWinAscent", "usWinDescent",
                  "sxHeight", "sCapHeight", "fsSelection", "usWeightClass"))
    gsub_same = table_bytes(j, "GSUB") == table_bytes(base, "GSUB")
    # Harena UI's GPOS lookups stay, in place
    gpos_j, gpos_h = j["GPOS"].table.LookupList.Lookup, base["GPOS"].table.LookupList.Lookup
    lookups = len(gpos_j) >= len(gpos_h) and all(
        _lookup_bytes(gpos_j[i], j) == _lookup_bytes(gpos_h[i], base) for i in range(len(gpos_h)))
    cases = json.loads((ROOT / "data/v0_3/cases.json").read_text())
    differ, shaped = [], 0

    def compare(text, lang, features):
        nonlocal shaped
        shaped += 1
        for t, s in runs_of(text) if any(ord(c) > 0x2E7F for c in text) else [(text, None)]:
            a, b = hb.Buffer(), hb.Buffer()
            for buf in (a, b):
                buf.add_str(t)
                buf.guess_segment_properties()
                if lang:
                    buf.language = lang
            hb.shape(face_j.font, a, features)
            hb.shape(face_h.font, b, features)
            if ([(i.codepoint, p.x_advance, p.x_offset, p.y_offset) for i, p in zip(a.glyph_infos, a.glyph_positions)]
                    != [(i.codepoint, p.x_advance, p.x_offset, p.y_offset) for i, p in zip(b.glyph_infos, b.glyph_positions)]):
                differ.append((text, lang))

    for case in cases["cases"]:
        if case["features"] is not None:
            compare(case["text"], case["lang"], case["features"])
    bases, marks = cases["marks"]["bases"], cases["marks"]["marks"]
    for lang in cases["marks"]["langs"]:
        for b in bases:
            for m in marks:
                compare(b + m, lang, {})
    # Latin in a CJK run keeps its kerning: the same glyphs under each script's system, each language
    line = "AVATo Windows 11, 1,234. (f) “g”"
    for script in ("Hang", "Hani", "Kana", "Hira", "Zyyy", "Latn"):
        for lang in SYSTEMS:
            a = face_j.shape(line, lang, script)
            b = face_h.shape(line, lang, script)
            if ([(i.codepoint, p.x_advance) for i, p in zip(a.glyph_infos, a.glyph_positions)]
                    != [(i.codepoint, p.x_advance) for i, p in zip(b.glyph_infos, b.glyph_positions)]):
                differ.append((line, script, lang))
    # Every code point of Harena UI's under each new system, alone
    for c in sorted(cmap_h):
        for script in ("Hang", "Hani", "Kana", "Zyyy", "Latn", "Cyrl", "Grek"):
            for lang in SYSTEMS:
                a = face_j.width(chr(c), lang, script)
                b = face_h.width(chr(c), lang, script)
                shaped += 1
                if a != b:
                    differ.append((chr(c), script, lang))
    r.check("13 Latin identity",
            same_order and not outlines and not advances and not remap and vertical and gsub_same and lookups and not differ,
            f"{len(order_h)} glyphs, {shaped} texts; order {same_order}, outlines {len(outlines)}, "
            f"advances {len(advances)}, cmap {len(remap)}, vertical {vertical}, GSUB {gsub_same}, "
            f"GPOS lookups {lookups}, shaped {len(differ)} {differ[:3]}")


def _lookup_bytes(lookup, font):
    out = io.StringIO()
    lookup.toXML(XMLWriter(out), font)
    return out.getvalue()


def check_coverage(r, j, base, cases):
    want = set(base.getBestCmap()) | set(cases["covered"])
    got = set(j.getBestCmap())
    orphans = len(j.getGlyphOrder()) - len(base.getGlyphOrder()) - len(cases["covered"])
    os2, name = j["OS/2"], j["name"]
    # Harena Term's ADR 0012: 932, 949 and 1361 declared, and not the Chinese ones
    pages = {932: 17, 936: 18, 949: 19, 950: 20, 1361: 21}
    declared = {p for p, bit in pages.items() if os2.ulCodePageRange1 & (1 << bit)}
    family = name.getDebugName(16) or ""
    named = family.startswith("Harena UI J ") and (name.getDebugName(6) or "").startswith("HarenaUIJ")
    # OFL 1.1 keeps each upstream notice, Pretendard JP's with its reservation
    notice = name.getDebugName(0) or ""
    named = named and "Open Sans Project Authors" in notice and "with Reserved Font Name Pretendard JP" in notice
    r.check("14 coverage", got == want and orphans == 0 and declared == {932, 949, 1361} and named,
            f"{len(got)} code points, {len(cases['covered'])} added; {len(got - want)} extra, "
            f"{len(want - got)} missing, {orphans} orphan glyphs; code pages {sorted(declared)}; family {family!r}")


def _near(units, px):
    return abs(units - px * PX) <= TOLERANCE


def check_widths(r, size, w, data, text_data, cases, face):
    covered, symbols, punctuation, kana = cases["covered"], set(cases["symbols"]), cases["punctuation"], cases["kana"]
    bad, tried, left_out = [], 0, {}
    # `en` stands for the languages with no CJK of their own: it must be no language
    bad += [("en", key) for key in ("alone", "sentences", "sequences") if data["en"][key] != data[""][key]]

    def out(reason):
        left_out[reason] = left_out.get(reason, 0) + 1

    for lang in SYSTEMS:
        d = data[lang]
        alone = expand(d["alone"])
        for c in covered:
            if c in MARKS:
                out("marks alone")
                continue
            if lang == "" and c in ALONE_ODD or (lang != "" and c in ALONE_ODD and alone[c] < 600):
                out("U+FF5F, U+FF60 alone")
                continue
            tried += 1
            got = face.width(chr(c), lang, own_script(c))
            if not _near(got, alone[c]):
                bad.append(("alone", lang, chr(c), got / PX, alone[c]))
        for name, script in (("hangul", "Hang"), ("han", "Hani")):
            base = cases["bases"][name][0]
            beside = d["beside"][name]
            for s in cases["symbols"]:
                if s in MARKS:
                    out("marks after a letter of no kana")
                    continue
                for text, key in ((base + chr(s), "after"), (chr(s) + base, "before")):
                    want = alone[ord(base)] + alone[s] + beside[key].get(str(s), 0)
                    got = face.width(text, lang, script)
                    tried += 1
                    if not _near(got, want):
                        if key == "before" and beside["after"].get(str(s), 0) != beside["before"].get(str(s), 0):
                            out("a symbol's font draws the letter after it")
                        else:
                            bad.append((name, key, lang, text, got / PX, want))
        pairs = d["kern"]
        for a in kana:
            for b in kana:
                text = chr(a) + chr(b)
                tried += 1
                got = face.run_width(text, lang)
                want = alone[a] + alone[b] + pairs.get(text, 0)
                if a in MARKS or b in MARKS:
                    continue
                if not _near(got, want):
                    bad.append(("kana", lang, text, got / PX, want))
        if size == "Text":
            run_shift = {s: Counter(round(pairs.get(chr(a) + chr(s), 0), 3) for a in kana).most_common(1)[0][0]
                         for s in cases["symbols"] if s not in MARKS}
            for a in kana:
                for s in cases["symbols"]:
                    if s in MARKS:
                        continue
                    for text in (chr(a) + chr(s), chr(s) + chr(a)):
                        tried += 1
                        got = face.width(text, lang, "Kana")
                        want = alone[a] + alone[s] + pairs.get(text, 0)
                        if not _near(got, want):
                            # Wider than the symbol is in a kana run: PLAN.md's Locked note
                            if pairs.get(text, 0) > run_shift[s] + 0.02:
                                out("a kana's font draws the symbol beside it")
                            else:
                                bad.append(("kana symbol", lang, text, got / PX, want))
        halted = {c: face.width(chr(c), lang, "Zyyy", {"halt": True}) - face.width(chr(c), lang, "Zyyy")
                  for c in punctuation}
        dot = "\u30FB"
        for group in ("pairs", "spaced"):
            for a in punctuation:
                for b in punctuation:
                    text = chr(a) + chr(b)
                    want = alone[a] + alone[b] + d[group].get(text, 0)
                    got = face.width(text, lang, "Zyyy")
                    tried += 1
                    if _near(got, want):
                        continue
                    if a in ALONE_ODD or b in ALONE_ODD:
                        out("U+FF5F, U+FF60 in a pair")
                        continue
                    if group == "pairs" and (_near(got + halted[a], want) or _near(got + halted[b], want)):
                        continue
                    if dot in text and lang != "ja":
                        out("U+30FB beside punctuation outside Japanese")
                        continue
                    # Neither nothing nor half an em: the first character's font draws the second
                    if abs(d[group].get(text, 0)) > 0.02 and abs(d[group].get(text, 0) + 500) > 0.02:
                        out("a symbol's font draws the symbol after it")
                        continue
                    bad.append((group, lang, text, got / PX, want))
        trims = {t for t, v in d["pairs"].items() if abs(v + 500) < 0.02}
        for key, group in (("sentences", cases["sentences"]), ("sequences", cases["sequences"])):
            for text, want in zip(group, d[key]):
                if key == "sentences" and any(ord(c) not in face.mapped for c in text):
                    out("text Pretendard JP lacks")
                    continue
                # Chinese text in Semibold and Bold: a font without U+309A gives it a whole em
                if lang.startswith("zh") and "\u309A" in text and alone[0x309A] > 0:
                    out("marks alone")
                    continue
                got = face.run_width(text, lang)
                got -= sum(1024 for a, b in zip(text, text[1:]) if a + b in trims)
                tried += 1
                if abs(got - want * PX) > 2:
                    bad.append((key, lang, text, got / PX, want))
    # `halt` under kana's default system: after kana, up to two punctuation marks on (PLAN.md)
    for text, want in (("ア）", -500), ("）、", 0), ("ア）、", -1000), ("ア「」、", -1500), ("ア「」、」", -1500),
                       ("か\u309A）、", -1000)):
        got = face.width(text, "", "Kana", {"halt": True}) - face.width(text, "", "Kana")
        tried += 1
        if not _near(got, want):
            bad.append(("halt", "", text, got / PX, want))
    # Runs as Chromium's iterator makes them, for what the sentences above rely on
    for text, want in (("「가A」", ["Hang", "Latn", "Hang"]), ("ア（F）、", ["Kana", "Latn", "Kana"]),
                       ("가「A」", ["Hang", "Latn", "Hang"]), ("F）、", ["Latn", "Zyyy"]),
                       ("「OK」 저장", ["Zyyy", "Latn", "Zyyy", "Hang"])):
        tried += 1
        if [s for _, s in runs_of(text)] != want:
            bad.append(("runs", "", text, runs_of(text), want))
    r.check("15 CJK widths", not bad,
            f"{tried} widths within half a unit of Windows', {len(bad)} not {bad[:4]}; left out as PLAN.md's: "
            + ", ".join(f"{k} {v}" for k, v in sorted(left_out.items())))


def check_features(r, j, base, data, text_data, cases):
    gsub_same = sorted(x.FeatureTag for x in j["GSUB"].table.FeatureList.FeatureRecord) == \
        sorted(x.FeatureTag for x in base["GSUB"].table.FeatureList.FeatureRecord)
    gpos = j["GPOS"].table
    tags = {x.FeatureTag for x in gpos.FeatureList.FeatureRecord}
    names = j.getBestCmap()
    by_name = {}
    for c, g in names.items():
        by_name.setdefault(g, c)
    base_kern = {x.FeatureTag: set(x.Feature.LookupListIndex) for x in base["GPOS"].table.FeatureList.FeatureRecord}["kern"]
    harena = set(base.getGlyphOrder())
    dists = {}
    problems = []
    for script in gpos.ScriptList.ScriptRecord:
        systems = {None: script.Script.DefaultLangSys}
        systems.update({x.LangSysTag: x.LangSys for x in script.Script.LangSysRecord})
        lang_of = {tag: lang for lang, tag in SYSTEMS.items()}
        if set(systems) != set(lang_of):
            problems.append((script.ScriptTag, "systems", sorted(str(k) for k in systems)))
        for tag, ls in systems.items():
            lang = lang_of[tag]
            halve = tag == "JAN " or (script.ScriptTag == "kana" and tag is None)
            halt_want = {int(k): v for k, v in data["ja"]["halt"].items()} if halve else {}
            halt_got = {}
            kern_extra, dist_lookups = set(), set()
            for i in ls.FeatureIndex:
                record = gpos.FeatureList.FeatureRecord[i]
                if record.FeatureTag == "halt":
                    for li in record.Feature.LookupListIndex:
                        lookup = gpos.LookupList.Lookup[li]
                        if script.ScriptTag == "kana" and tag is None:
                            # kana's default system: `halt` only after kana (PLAN.md)
                            if lookup.LookupType != 8 or len(lookup.SubTable) != 3 or lookup.LookupFlag != 8:
                                problems.append(("kana", tag, "halt without its context"))
                                continue
                            for between, st_ in enumerate(lookup.SubTable):
                                back = [{by_name[g] for g in c.glyphs} for c in st_.BacktrackCoverage]
                                if (back != [set(cases["punctuation"])] * between + [set(cases["kana"])]
                                        or {by_name[g] for g in st_.InputCoverage[0].glyphs} != set(halt_want)
                                        or st_.LookAheadCoverage
                                        or [(x.SequenceIndex, x.LookupListIndex) for x in st_.PosLookupRecord]
                                        != [(0, lookup.SubTable[0].PosLookupRecord[0].LookupListIndex)]):
                                    problems.append(("kana", tag, "halt's context is not kana's", between))
                            lookup = gpos.LookupList.Lookup[lookup.SubTable[0].PosLookupRecord[0].LookupListIndex]
                        for st_ in lookup.SubTable:
                            for g, v in _single_values(st_):
                                halt_got[by_name[g]] = halt_got.get(by_name[g], 0) + v.XAdvance
                elif record.FeatureTag == "kern":
                    kern_extra |= set(record.Feature.LookupListIndex) - base_kern
                elif record.FeatureTag == "dist":
                    dist_lookups |= set(record.Feature.LookupListIndex)
            touched = {g for li in dist_lookups for st_ in gpos.LookupList.Lookup[li].SubTable
                       for g, _ in _single_values(st_)}
            if touched & harena:
                problems.append((script.ScriptTag, tag, "dist on Harena UI's glyphs", sorted(touched & harena)[:3]))
            dists[script.ScriptTag, tag] = dist_lookups
            if set(halt_got) != set(halt_want) or any(v != -UPM // 2 for v in halt_got.values()):
                problems.append((script.ScriptTag, tag, "halt", len(halt_got), len(halt_want)))
            # kana with symbols are measured on Text, for each size
            want_kern = kana_kern(text_data[lang], cases) if script.ScriptTag == "kana" else {}
            got_kern = {}
            for li in kern_extra:
                for st_ in gpos.LookupList.Lookup[li].SubTable:
                    for (a, b), v in _pair_values(st_).items():
                        got_kern[chr(by_name[a]) + chr(by_name[b])] = got_kern.get(chr(by_name[a]) + chr(by_name[b]), 0) + v
            if got_kern != want_kern:
                problems.append((script.ScriptTag, tag, "kana kern", len(got_kern), len(want_kern)))
    # Every system keeps its script's own features, or DFLT's, in Harena UI's lookups
    def own(table):
        out = {}
        for script in table.ScriptList.ScriptRecord:
            features = [table.FeatureList.FeatureRecord[i] for i in script.Script.DefaultLangSys.FeatureIndex]
            out[script.ScriptTag] = {x.FeatureTag: set(x.Feature.LookupListIndex) for x in features}
        return out

    inherited = own(base["GPOS"].table)
    harena_lookups = set(range(len(base["GPOS"].table.LookupList.Lookup)))
    for script in gpos.ScriptList.ScriptRecord:
        systems = [(None, script.Script.DefaultLangSys)] + [(x.LangSysTag, x.LangSys) for x in script.Script.LangSysRecord]
        want = inherited.get(script.ScriptTag, inherited["DFLT"])
        for tag, ls in systems:
            have = {}
            for i in ls.FeatureIndex:
                record = gpos.FeatureList.FeatureRecord[i]
                have.setdefault(record.FeatureTag, set()).update(record.Feature.LookupListIndex)
            for feature, lookups in want.items():
                if have.get(feature, set()) & harena_lookups != lookups:
                    problems.append((script.ScriptTag, tag, f"{feature} is not Harena UI's"))
    # A script of Harena UI's own takes what a run of no script takes
    for (script, tag), lookups in dists.items():
        if script not in ("hang", "hani", "kana") and lookups != dists["DFLT", tag]:
            problems.append((script, tag, "dist differs from DFLT's"))
    want_tags = {"kern", "mark", "mkmk", "dist", "halt"}
    r.check("16 features", gsub_same and tags == want_tags and not problems,
            f"GSUB as Harena UI's: {gsub_same}; GPOS {sorted(tags)}; {len(problems)} problems {problems[:4]}")


def kana_kern(d, cases):
    """What in a language's kana pairs is kerning, not a symbol's width in the run: a symbol's most
    usual change after kana is the run's."""
    kana, symbols = cases["kana"], [s for s in cases["symbols"] if s not in MARKS]
    shift = {s: Counter(round(d["kern"].get(chr(a) + chr(s), 0), 3) for a in kana).most_common(1)[0][0]
             for s in symbols}
    out = {}
    for text, v in d["kern"].items():
        a, b = map(ord, text)
        if a in MARKS or b in MARKS:
            continue
        rest = otRound((v - shift.get(a if a in shift else b, 0)) * PX)
        if rest < 0:
            out[text] = rest
    return out


def _pair_values(subtable):
    if subtable.__class__.__name__ == "ExtensionPos":
        subtable = subtable.ExtSubTable
    out = {}
    for first, pair_set in zip(subtable.Coverage.glyphs, subtable.PairSet):
        for record in pair_set.PairValueRecord:
            out[first, record.SecondGlyph] = record.Value1.XAdvance
    return out


def _single_values(subtable):
    if subtable.__class__.__name__ == "ExtensionPos":
        subtable = subtable.ExtSubTable
    if subtable.Format == 1:
        return [(g, subtable.Value) for g in subtable.Coverage.glyphs]
    return list(zip(subtable.Coverage.glyphs, subtable.Value))


_instances = {}


def _instance(wght):
    if wght not in _instances:
        cases = json.loads((DATA / "cases.json").read_text())
        font = TTFont(PJP)
        options = subset.Options(layout_features=[], name_IDs=[], glyph_names=True, hinting=False)
        sub = subset.Subsetter(options)
        sub.populate(unicodes=cases["covered"])
        sub.subset(font)
        instantiateVariableFont(font, {"wght": wght}, inplace=True)
        _instances[wght] = font
    return _instances[wght]


def check_shapes(r, size, w, j, chosen, shapes, cases):
    def hangul(c):
        return fu.script(chr(c)) == "Hang"

    row = STEM_ROW_PX * PX
    cmap = j.getBestCmap()
    stems = shapes["stems"]
    malgun = stems[f"Malgun Gothic|{w}"][HANGUL_STEM]
    yu = stems[f"Yu Gothic|{w}"][HAN_STEM]
    stem_h = row_coverage(j, cmap[ord(HANGUL_STEM)], row) / PX
    stem_y = row_coverage(j, cmap[ord(HAN_STEM)], row) / PX
    stems_ok = abs(stem_h / malgun - 1) <= STEM_TOLERANCE and abs(stem_y / yu - 1) <= STEM_TOLERANCE
    gs = j.getGlyphSet()
    ink = shapes["ink"][f"Malgun Gothic|{w}"]
    ko = [ord(c) for c in shapes["ink_sample"]["ko"]]

    def box(c):
        pen = BoundsPen(gs)
        gs[cmap[c]].draw(pen)
        return pen.bounds

    body_h = st.median(box(c)[3] - box(c)[1] for c in ko) / PX
    want_h = st.median(ink[str(c)][2] - ink[str(c)][3] for c in ko)
    body_ok = abs(body_h / want_h - 1) <= BODY_TOLERANCE
    scale = chosen["hangul_scale"]
    src = {True: _instance(chosen["hangul_wght"]), False: _instance(chosen["han_wght"])}
    moved = []
    for c in cases["covered"]:
        is_h = hangul(c)
        s = scale if is_h else 1.0
        source = src[is_h]
        have, ops_h = outline(j, gs, cmap[c])
        want, ops_w = outline(source, source.getGlyphSet(), source.getBestCmap()[c], s)
        if ops_h != ops_w or len(have) != len(want):
            moved.append((chr(c), "structure"))
            continue
        if not have:
            continue
        dx = sum(a[0] - b[0] for a, b in zip(have, want)) / len(have)
        if any(abs(a[0] - b[0] - dx) > OUTLINE_TOLERANCE or abs(a[1] - b[1]) > OUTLINE_TOLERANCE
               for a, b in zip(have, want)):
            moved.append((chr(c), "points"))
    r.check("17 shapes", stems_ok and body_ok and not moved,
            f"stems {stem_h:.1f}/{malgun:.1f} and {stem_y:.1f}/{yu:.1f}; Hangul body {body_h:.1f}/{want_h:.1f}; "
            f"{len(cases['covered'])} outlines, {len(moved)} not Pretendard JP's {moved[:4]}")


def face_j(size, w):
    r = Report(f"J-{size}-{WEIGHTS[w]}")
    cases = json.loads((DATA / "cases.json").read_text())
    data, text_data = windows(size, w), windows("Text", w)
    j, base = TTFont(j_path(size, w)), TTFont(face_path(size, w))
    face = Face(j_path(size, w))
    face.mapped = set(j.getBestCmap())
    harena = Face(face_path(size, w))
    r.guarded("13 Latin identity", lambda: check_latin(r, j, base, face, harena))
    r.guarded("14 coverage", lambda: check_coverage(r, j, base, cases))
    r.guarded("15 CJK widths", lambda: check_widths(r, size, w, data, text_data, cases, face))
    r.guarded("16 features", lambda: check_features(r, j, base, data, text_data, cases))
    build = json.loads((DATA / "build.json").read_text())[str(w)]
    shapes = json.loads((DATA / "shapes.json").read_text())
    r.guarded("17 shapes", lambda: check_shapes(r, size, w, j, build, shapes, cases))
    return r.lines, r.failed


def reproducible_j():
    r = Report("J")
    paths = [j_path(*f) for f in FACES]

    def run():
        hashes = []
        for _ in range(2):
            done = subprocess.run([sys.executable, str(ROOT / "scripts/build_j.py")], capture_output=True, text=True)
            if done.returncode:
                raise RuntimeError(f"build failed: {done.stderr.strip().splitlines()[-1:]}")
            hashes.append([hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])

        def git(*a):
            return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).returncode

        tracked = ("SHA256SUMS-J", "data/v0_4/build.json")
        committed = all(git("cat-file", "-e", f"HEAD:{p}") == 0 for p in tracked)
        same_as_head = git("diff", "--quiet", "HEAD", "--", *tracked) == 0
        want = "".join(f"{h}  {p.relative_to(ROOT)}\n" for h, p in zip(hashes[0], paths))
        listed = (ROOT / "SHA256SUMS-J").read_text() == want
        r.check("18 reproducible", hashes[0] == hashes[1] and committed and same_as_head and listed,
                f"two builds of {len(paths)} faces {'identical' if hashes[0] == hashes[1] else 'differ'}; "
                + ("SHA256SUMS-J lists them" if listed else "SHA256SUMS-J does not list exactly these") + "; "
                + ("not committed" if not committed else
                   "SHA256SUMS-J and build.json equal HEAD's" if same_as_head else "differ from HEAD"))
    r.guarded("18 reproducible", run)
    return r.lines, r.failed


if __name__ == "__main__":
    wanted = sys.argv[1:]
    failed = []
    for size, w in FACES:
        if not wanted or f"{size}-{WEIGHTS[w]}" in wanted:
            out_lines, bad = face_j(size, w)
            print("\n".join(out_lines), flush=True)
            failed += bad
    print("gate:", "FAIL" if failed else "PASS")
    sys.exit(1 if failed else 0)
