# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""The gate's checks over Harena UI J, v0.7: 13 Latin identity, 14 coverage, 15 CJK widths,
16 features and 17 shapes, per face; 18 reproducible, once. Run by scripts/verify.py after
Harena UI's checks.

Like verify.py, this takes no expectation from the build. It reads the fonts, what WinUI 3 lays
out (data/v0_7), and data/v0_4/build.json, whose claims it checks. It instances Pretendard JP
itself for check 17.

HarfBuzz does not split text into runs: run_width() below splits it the way Chromium's
ScriptRunIterator does. The check in Edge (PLAN.md, v0.7 item 5) is what shows a browser does too.

Usage: python scripts/verify_j.py [Size-Weight ...]
"""
import hashlib
import io
import json
import statistics as st
import subprocess
import sys
import unicodedata
from functools import lru_cache
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
WINUI = ROOT / "data/v0_7"
PJP = ROOT / "sources/pjp/public/variable/PretendardJPVariable.ttf"
SIZES = ("Small", "Text", "Display")
WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
FACES = [(size, w) for size in SIZES for w in WEIGHTS]
UPM = 2048
PX = UPM / 1000
SYSTEMS = {"": None, "ko": "KOR ", "ja": "JAN ", "zh-Hans": "ZHS ", "zh-Hant": "ZHT "}
HB_LANG = {"": "en", "ko": "ko", "ja": "ja", "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant"}
# WinUI's languages, as HarfBuzz is told them
WINUI_LANGS = {"none": "", "ko-KR": "ko", "ja-JP": "ja"}
TOLERANCE = 0.5 + 1e-6  # font units
HANGUL_STEM = "ㅣ"
HAN_STEM = "十"
STEM_ROW_PX = 650
STEM_TOLERANCE = 0.03
BODY_TOLERANCE = 0.02
# Rounded in the build after scaling and moving, and instanced here unrounded
OUTLINE_TOLERANCE = 1.5
MARKS = (0x3099, 0x309A)
# Their ink is at the trailing edge, as a closing bracket's (PLAN.md, v0.4)
TRAILING_DOTS = (0x3001, 0x3002, 0xFF0C, 0xFF0E)
# Unicode's paired brackets, which is what Chromium's iterator reads
OPEN = "([{〈《「『【〔〖〘〚（［｛｟"
CLOSE = ")]}〉》」』】〕〗〙〛）］｝｠"


def face_path(size, w):
    return ROOT / "dist" / f"HarenaUI-{size}{WEIGHTS[w]}.ttf"


def j_path(size, w):
    return ROOT / "dist" / f"HarenaUIJ-{size}{WEIGHTS[w]}.ttf"


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


@lru_cache(maxsize=None)
def winui():
    """What WinUI 3 lays out (data/v0_7), and the pairs it was measured on, with probe/v0_7's
    rule for which those are."""
    sys.path.insert(0, str(ROOT / "probe/v0_7"))
    from run import pair_points
    data = json.loads((WINUI / "winui.json").read_text())
    pairs = json.loads((WINUI / "pairs.json").read_text())
    measured = pair_points()
    assert len(measured) == pairs["pairs"], "the pairs are not the ones measured"
    return data, pairs, measured


def check_widths(r, w, cases, face):
    """Every covered code point, alone and with `kern` off, in each language WinUI was measured in,
    at WinUI's width; under its own script and, for punctuation and symbols, in a run of each CJK
    script. Every measured pair, split into runs as Chromium splits it, at the sum of its parts and what WinUI
    lays the pair out apart from them. A kana and a combining sound mark that Unicode composes are
    the composed letter, as HarfBuzz composes them (PLAN.md, v0.7)."""
    data, pairs, measured = winui()
    scale = UPM / data["size"]
    bad, tried = [], 0
    for lang, hb_lang in WINUI_LANGS.items():
        widths = {int(k, 16): px for k, px in data["widths"][lang][str(w)].items()}
        differ = pairs["differ"].get(lang, {}).get(str(w), {})
        for c in cases["covered"]:
            for script in [own_script(c)] + (["Hang", "Hani", "Kana"] if own_script(c) == "Zyyy" else []):
                # with `kern` off, as a page may set it: a width only `kern` gave would be lost
                got = face.width(chr(c), hb_lang, script, {"kern": False})
                tried += 1
                if abs(got - widths[c] * scale) > TOLERANCE:
                    bad.append((lang, script, chr(c), got / scale, widths[c]))
        for a, b in measured:
            composed = unicodedata.normalize("NFC", chr(a) + chr(b))
            if len(composed) == 1 and ord(composed) in widths:
                want = widths[ord(composed)] * scale
            else:
                want = (widths[a] + widths[b] + differ.get(f"{a:04X}+{b:04X}", 0)) * scale
            got = face.run_width(chr(a) + chr(b), hb_lang)
            tried += 1
            # each of the three rounded to a unit in the build
            if abs(got - want) > 3 * TOLERANCE:
                bad.append((lang, chr(a) + chr(b), got / scale, want / scale))
    r.check("15 CJK widths", not bad,
            f"{tried} widths and pairs within rounding of WinUI's, {len(bad)} not {bad[:4]}")


def check_features(r, j, base, cases):
    """GSUB is Harena UI's. Every script has no language's system and JAN's, each with Harena UI's
    features for that script and no required feature; `dist` only under JAN, one and the same in
    every script, and nothing else that changes widths (`halt`, `palt` and their kin). Only `kern`
    and `dist` have lookups Harena UI's lack, of the kinds the build adds, touching only CJK."""
    gsub_same = sorted(x.FeatureTag for x in j["GSUB"].table.FeatureList.FeatureRecord) == \
        sorted(x.FeatureTag for x in base["GSUB"].table.FeatureList.FeatureRecord)
    gpos, base_gpos = j["GPOS"].table, base["GPOS"].table
    tags = {x.FeatureTag for x in gpos.FeatureList.FeatureRecord}
    base_tags = {x.FeatureTag for x in base_gpos.FeatureList.FeatureRecord}
    harena = set(base.getGlyphOrder())
    base_scripts = {x.ScriptTag: x.Script for x in base_gpos.ScriptList.ScriptRecord}
    problems = []

    def features(gpos_, ls):
        out = {}
        for i in ls.FeatureIndex:
            record = gpos_.FeatureList.FeatureRecord[i]
            out.setdefault(record.FeatureTag, set()).update(record.Feature.LookupListIndex)
        return out

    def glyphs(lookup, tag):
        """Every glyph a lookup added to `kern` or `dist` adjusts; None for one that is not what the
        build adds there: glyph pairs that change the first glyph's advance alone, under `kern`, and
        single adjustments of advance and placement, under `dist`. (A class pair's class 0 is every
        glyph the classes leave out, so it is never read as CJK only.)"""
        out = set()
        for st_ in lookup.SubTable:
            st_ = st_.ExtSubTable if st_.__class__.__name__ == "ExtensionPos" else st_
            kind = st_.__class__.__name__
            if tag == "kern" and not (kind == "PairPos" and st_.Format == 1 and st_.ValueFormat1 == 4
                                      and st_.ValueFormat2 == 0):
                return None
            if tag == "dist" and not (kind == "SinglePos" and st_.ValueFormat & ~5 == 0):
                return None
            out.update(st_.Coverage.glyphs)
            for pair_set in getattr(st_, "PairSet", []):
                out.update(rec.SecondGlyph for rec in pair_set.PairValueRecord)
        return out

    scripts = {x.ScriptTag: x.Script for x in gpos.ScriptList.ScriptRecord}
    if len(scripts) != len(gpos.ScriptList.ScriptRecord):
        problems.append(("a script twice",))
    jan_dist = set()
    if set(scripts) != set(base_scripts) | {"hang", "hani", "kana"}:
        problems.append(("scripts", sorted(scripts)))
    for tag, script in scripts.items():
        systems = {None: script.DefaultLangSys}
        systems.update({x.LangSysTag: x.LangSys for x in script.LangSysRecord})
        # a renderer takes one of a tag's records, and this reads another
        if len(systems) != len(script.LangSysRecord) + 1:
            problems.append((tag, "a system twice"))
        if set(systems) != {None, "JAN "}:
            problems.append((tag, "systems", sorted(str(k) for k in systems)))
        want = features(base_gpos, base_scripts.get(tag, base_scripts["DFLT"]).DefaultLangSys)
        for system, ls in systems.items():
            got = features(gpos, ls)
            # a required feature applies whatever a page turns off
            if ls.ReqFeatureIndex != 0xFFFF:
                problems.append((tag, system, "a required feature"))
            if set(got) - set(want) - ({"dist"} if system == "JAN " else set()):
                problems.append((tag, system, "features", sorted(set(got) - set(want))))
            for t, lookups in want.items():
                if not lookups <= got.get(t, set()):
                    problems.append((tag, system, t, "lacks Harena UI's lookups"))
                elif t != "kern" and got[t] != lookups:
                    problems.append((tag, system, t, "has lookups Harena UI's lacks"))
            for t in ("kern", "dist"):
                for li in got.get(t, set()) - want.get(t, set()):
                    touched = glyphs(gpos.LookupList.Lookup[li], t)
                    if touched is None:
                        problems.append((tag, system, t, "not what the build adds"))
                    elif touched & harena:
                        problems.append((tag, system, t, "touches Harena UI's glyphs"))
            if system == "JAN ":
                jan_dist.add(frozenset(got.get("dist", set())))
    # Japanese's widths are one `dist`, the same in every script's JAN
    if len(jan_dist) != 1 or not next(iter(jan_dist)):
        problems.append(("JAN", "dist", "not one and the same in every script"))
    r.check("16 features", gsub_same and tags <= base_tags | {"dist"} and not problems,
            f"GSUB {gsub_same}; GPOS {sorted(tags)}; {len(problems)} problems {problems[:4]}")


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


def placed(c, advance, source_advance):
    """How far right of its source position the locked rule puts a glyph's ink in an advance:
    opening punctuation keeps its trailing bearing, closing punctuation its leading one, and
    everything else its source's balance, centred (PLAN.md, v0.4 and v0.7)."""
    kind = unicodedata.category(chr(c))
    if kind in ("Ps", "Pi"):
        return advance - source_advance
    if kind in ("Pe", "Pf") or c in TRAILING_DOTS:
        return 0
    return (advance - source_advance) / 2


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
        source_advance = source["hmtx"][source.getBestCmap()[c]][0] * s
        advance = j["hmtx"][cmap[c]][0]
        if c in MARKS:
            # they hang back over the letter before, whose middle moved back by half what it grew
            want_dx = -(UPM - source["hmtx"][source.getBestCmap()[0x3042]][0]) / 2
        else:
            want_dx = placed(c, advance, source_advance)
        if abs(dx - want_dx) > OUTLINE_TOLERANCE:
            moved.append((chr(c), "placed", round(dx - want_dx)))
            continue
        if any(abs(a[0] - b[0] - dx) > OUTLINE_TOLERANCE or abs(a[1] - b[1]) > OUTLINE_TOLERANCE
               for a, b in zip(have, want)):
            moved.append((chr(c), "points"))
    # Under JAN, the ink goes where the rule puts it in Japanese's advance: check 16 holds every
    # script's JAN to one `dist` of single adjustments, read here whole
    gpos = j["GPOS"].table
    glyph_c = {g: c for c, g in cmap.items()}
    adjusted = set()  # once each, so that the record read is all the glyph gets
    for record in gpos.FeatureList.FeatureRecord:
        if record.FeatureTag != "dist":
            continue
        for li in record.Feature.LookupListIndex:
            for sub in gpos.LookupList.Lookup[li].SubTable:
                sub = sub.ExtSubTable if sub.__class__.__name__ == "ExtensionPos" else sub
                values = sub.Value if sub.Format == 2 else [sub.Value] * len(sub.Coverage.glyphs)
                for g, v in zip(sub.Coverage.glyphs, values):
                    c = glyph_c.get(g)
                    if c is None or c in MARKS or g in adjusted:
                        moved.append((g, "adjusted under JAN", "again" if g in adjusted else ""))
                        continue
                    adjusted.add(g)
                    is_h = hangul(c)
                    source = src[is_h]
                    source_advance = source["hmtx"][source.getBestCmap()[c]][0] * (scale if is_h else 1.0)
                    advance, d = j["hmtx"][g][0], getattr(v, "XAdvance", 0) or 0
                    want = placed(c, advance + d, source_advance) - placed(c, advance, source_advance)
                    if abs((getattr(v, "XPlacement", 0) or 0) - want) > 1:
                        moved.append((chr(c), "placed under JAN", getattr(v, "XPlacement", 0)))
    r.check("17 shapes", stems_ok and body_ok and not moved,
            f"stems {stem_h:.1f}/{malgun:.1f} and {stem_y:.1f}/{yu:.1f}; Hangul body {body_h:.1f}/{want_h:.1f}; "
            f"{len(cases['covered'])} outlines, {len(moved)} not Pretendard JP's or not placed as locked {moved[:4]}")


def face_j(size, w):
    r = Report(f"J-{size}-{WEIGHTS[w]}")
    cases = json.loads((DATA / "cases.json").read_text())
    j, base = TTFont(j_path(size, w)), TTFont(face_path(size, w))
    face = Face(j_path(size, w))
    face.mapped = set(j.getBestCmap())
    harena = Face(face_path(size, w))
    r.guarded("13 Latin identity", lambda: check_latin(r, j, base, face, harena))
    r.guarded("14 coverage", lambda: check_coverage(r, j, base, cases))
    r.guarded("15 CJK widths", lambda: check_widths(r, w, cases, face))
    r.guarded("16 features", lambda: check_features(r, j, base, cases))
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
