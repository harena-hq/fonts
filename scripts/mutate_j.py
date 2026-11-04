#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Prove the J gate's width, feature and placement checks catch what they claim to: each mutation, made
to a copy of J Text Regular, must fail its own check.

Usage: python scripts/mutate_j.py
"""
import copy
import json
import sys
import tempfile
from pathlib import Path

from fontTools.otlLib import builder as otl
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

import verify_j

SIZE, W = "Text", 400


def systems(font):
    for record in font["GPOS"].table.ScriptList.ScriptRecord:
        yield record.Script, None, record.Script.DefaultLangSys
        for ls in record.Script.LangSysRecord:
            yield record.Script, ls.LangSysTag, ls.LangSys


def add_feature(font, tag, lookup, where):
    """A new feature with one new lookup, in the systems `where` picks."""
    gpos = font["GPOS"].table
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    feature = ot.Feature()
    feature.FeatureParams, feature.LookupListIndex, feature.LookupCount = None, [gpos.LookupList.LookupCount - 1], 1
    record = ot.FeatureRecord()
    record.FeatureTag, record.Feature = tag, feature
    gpos.FeatureList.FeatureRecord.append(record)
    gpos.FeatureList.FeatureCount = len(gpos.FeatureList.FeatureRecord)
    for _, system, ls in systems(font):
        if where(system):
            ls.FeatureIndex.append(gpos.FeatureList.FeatureCount - 1)
            ls.FeatureCount = len(ls.FeatureIndex)


def add_to(font, tag, lookup, where=lambda system: True):
    """One new lookup, in the existing `tag` features of the systems `where` picks."""
    gpos = font["GPOS"].table
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    records = gpos.FeatureList.FeatureRecord
    for _, system, ls in systems(font):
        if where(system):
            for i in ls.FeatureIndex:
                if records[i].FeatureTag == tag and gpos.LookupList.LookupCount - 1 not in records[i].Feature.LookupListIndex:
                    records[i].Feature.LookupListIndex.append(gpos.LookupList.LookupCount - 1)
                    records[i].Feature.LookupCount = len(records[i].Feature.LookupListIndex)


def single(font, chars, d):
    cmap = font.getBestCmap()
    return otl.buildLookup(otl.buildSinglePos({cmap[ord(c)]: otl.buildValue({"XAdvance": d}) for c in chars},
                                              font.getReverseGlyphMap()))


def width_off(font):
    name = font.getBestCmap()[0x3042]
    font["hmtx"][name] = (font["hmtx"][name][0] + 1, font["hmtx"][name][1])


def jan_dropped(font):
    gpos = font["GPOS"].table
    for _, system, ls in systems(font):
        if system == "JAN ":
            ls.FeatureIndex = [i for i in ls.FeatureIndex if gpos.FeatureList.FeatureRecord[i].FeatureTag != "dist"]
            ls.FeatureCount = len(ls.FeatureIndex)


def pair_dropped(font):
    # The first pair of the last lookup kern has: JAN's pairs, built after no language's
    gpos = font["GPOS"].table
    kern = [r for r in gpos.FeatureList.FeatureRecord if r.FeatureTag == "kern"]
    last = max(i for r in kern for i in r.Feature.LookupListIndex)
    st = gpos.LookupList.Lookup[last].SubTable[0]
    st = st.ExtSubTable if st.__class__.__name__ == "ExtensionPos" else st
    st.PairSet[0].PairValueRecord.pop(0)
    st.PairSet[0].PairValueCount = len(st.PairSet[0].PairValueRecord)


def halt_added(font):
    add_feature(font, "halt", single(font, "「」", -100), lambda system: system == "JAN ")


def kor_system(font):
    for script, _, ls in list(systems(font)):
        if ls is script.DefaultLangSys:
            record = ot.LangSysRecord()
            record.LangSysTag, record.LangSys = "KOR ", ls
            script.LangSysRecord.append(record)
            script.LangSysRecord.sort(key=lambda r: r.LangSysTag)
            script.LangSysCount = len(script.LangSysRecord)


def dist_default(font):
    add_feature(font, "dist", single(font, "あ", -100), lambda system: system is None)


def latin_kerned(font):
    cmap = font.getBestCmap()
    lookup = otl.buildLookup(otl.buildPairPosGlyphs({(cmap[ord("A")], cmap[0x3042]): (otl.buildValue({"XAdvance": -50}), None)},
                                                    font.getReverseGlyphMap()))
    add_feature(font, "kern", lookup, lambda system: True)


def dist_as_kern(font):
    # JAN's widths moved into its kern, which a page can turn off
    gpos = font["GPOS"].table
    for _, system, ls in systems(font):
        if system == "JAN ":
            records = gpos.FeatureList.FeatureRecord
            dist = [i for i in ls.FeatureIndex if records[i].FeatureTag == "dist"]
            kern = [i for i in ls.FeatureIndex if records[i].FeatureTag == "kern"]
            for d in dist:
                for k in kern:
                    records[k].Feature.LookupListIndex = sorted(set(records[k].Feature.LookupListIndex)
                                                                | set(records[d].Feature.LookupListIndex))
                    records[k].Feature.LookupCount = len(records[k].Feature.LookupListIndex)
            ls.FeatureIndex = [i for i in ls.FeatureIndex if i not in dist]
            ls.FeatureCount = len(ls.FeatureIndex)


def class_kerned(font):
    # A CJK glyph's class against class 0, which holds every glyph, Harena UI's among them
    cmap = font.getBestCmap()
    glyph_map = font.getReverseGlyphMap()
    st = otl.buildPairPosClassesSubtable({((cmap[0xFF21],), (cmap[0x3042],)): (otl.buildValue({"XAdvance": 0}), None)},
                                         glyph_map)
    st.Class1Record[0].Class2Record[0].Value1 = otl.buildValue({"XAdvance": -500})
    st.ValueFormat1 = 4
    add_to(font, "kern", otl.buildLookup([st]))


def required_kern(font):
    # dist_as_kern, with kern then required, so that turning it off does not
    dist_as_kern(font)
    records = font["GPOS"].table.FeatureList.FeatureRecord
    for _, system, ls in systems(font):
        if system == "JAN ":
            ls.ReqFeatureIndex = next(i for i in ls.FeatureIndex if records[i].FeatureTag == "kern")


def mark_added(font):
    # Ａ against everything but CJK, by class 0, in the existing mark feature
    cmap = font.getBestCmap()
    cjk = tuple(font.getBestCmap()[c] for c in json.loads((verify_j.DATA / "cases.json").read_text())["covered"])
    st = otl.buildPairPosClassesSubtable({((cmap[0xFF21],), cjk): (otl.buildValue({"XAdvance": 0}), None)},
                                         font.getReverseGlyphMap())
    st.Class1Record[0].Class2Record[0].Value1 = otl.buildValue({"XAdvance": -500})
    st.ValueFormat1 = 4
    add_to(font, "mark", otl.buildLookup([st]))


def kern_placed(font):
    # あ's ink moved under no language, by an XPlacement in its kern
    cmap = font.getBestCmap()
    add_to(font, "kern", otl.buildLookup(otl.buildSinglePos({cmap[0x3042]: otl.buildValue({"XPlacement": 500})},
                                                            font.getReverseGlyphMap())),
           lambda system: system is None)


def hani_moved(font):
    # 、's ink moved under JAN in a Han run only, its width kept
    gpos = font["GPOS"].table
    name = font.getBestCmap()[0x3001]
    record = next(r for r in gpos.FeatureList.FeatureRecord if r.FeatureTag == "dist")
    lookup = copy.deepcopy(gpos.LookupList.Lookup[record.Feature.LookupListIndex[0]])
    for st in lookup.SubTable:
        st = st.ExtSubTable if st.__class__.__name__ == "ExtensionPos" else st
        if name in st.Coverage.glyphs:
            v = st.Value[st.Coverage.glyphs.index(name)] if st.Format == 2 else st.Value
            v.XPlacement = (getattr(v, "XPlacement", 0) or 0) + 500
            st.ValueFormat |= 1
    hani = next(r.Script for r in gpos.ScriptList.ScriptRecord if r.ScriptTag == "hani")
    jan = next(r.LangSys for r in hani.LangSysRecord if r.LangSysTag == "JAN ")
    jan.FeatureIndex = [i for i in jan.FeatureIndex if gpos.FeatureList.FeatureRecord[i].FeatureTag != "dist"]
    add_feature(font, "dist", lookup, lambda system: False)
    jan.FeatureIndex.append(gpos.FeatureList.FeatureCount - 1)
    jan.FeatureCount = len(jan.FeatureIndex)


def mark_in_dist(font):
    # U+3099 moved under JAN, its width kept at 0
    cmap = font.getBestCmap()
    add_to(font, "dist", otl.buildLookup(otl.buildSinglePos({cmap[0x3099]: otl.buildValue({"XPlacement": 500})},
                                                            font.getReverseGlyphMap())),
           lambda system: system == "JAN ")


def jan_moved(font):
    # JAN's widths kept, its ink moved
    gpos = font["GPOS"].table
    for record in gpos.FeatureList.FeatureRecord:
        if record.FeatureTag == "dist":
            for li in record.Feature.LookupListIndex:
                for st in gpos.LookupList.Lookup[li].SubTable:
                    st = st.ExtSubTable if st.__class__.__name__ == "ExtensionPos" else st
                    values = st.Value if isinstance(st.Value, list) else [st.Value]
                    for v in values:
                        v.XPlacement = getattr(v, "XPlacement", 0) + 500
                    st.ValueFormat |= 1


def ink_moved(font):
    # あ's outline moved right in its advance
    name = font.getBestCmap()[0x3042]
    glyph = font["glyf"][name]
    glyph.coordinates.translate((200, 0))
    glyph.recalcBounds(font["glyf"])
    font["hmtx"][name] = (font["hmtx"][name][0], glyph.xMin)


def dist_stacked(font):
    # あ moved 500 units under JAN by 500 lookups of one unit each
    cmap = font.getBestCmap()
    for _ in range(500):
        add_to(font, "dist", otl.buildLookup(otl.buildSinglePos({cmap[0x3042]: otl.buildValue({"XPlacement": 1})},
                                                                font.getReverseGlyphMap())),
               lambda system: system == "JAN ")


def jan_twice(font):
    # hani with a second JAN record before its own, whose kern moves 、's ink
    gpos = font["GPOS"].table
    cmap = font.getBestCmap()
    hani = next(r.Script for r in gpos.ScriptList.ScriptRecord if r.ScriptTag == "hani")
    own = next(r for r in hani.LangSysRecord if r.LangSysTag == "JAN ")
    lookup = otl.buildLookup(otl.buildSinglePos({cmap[0x3001]: otl.buildValue({"XPlacement": 500})},
                                                font.getReverseGlyphMap()))
    add_feature(font, "kern", lookup, lambda system: False)
    record = ot.LangSysRecord()
    record.LangSysTag, record.LangSys = "JAN ", copy.deepcopy(own.LangSys)
    record.LangSys.FeatureIndex.append(gpos.FeatureList.FeatureCount - 1)
    record.LangSys.FeatureCount = len(record.LangSys.FeatureIndex)
    hani.LangSysRecord.insert(hani.LangSysRecord.index(own), record)
    hani.LangSysCount = len(hani.LangSysRecord)


MUTATIONS = [
    (width_off, "15 CJK widths"),
    (jan_dropped, "15 CJK widths"),
    (pair_dropped, "15 CJK widths"),
    (halt_added, "16 features"),
    (kor_system, "16 features"),
    (dist_default, "16 features"),
    (latin_kerned, "16 features"),
    (dist_as_kern, "15 CJK widths"),
    (class_kerned, "16 features"),
    (jan_moved, "17 shapes"),
    (ink_moved, "17 shapes"),
    (required_kern, "16 features"),
    (mark_added, "16 features"),
    (kern_placed, "16 features"),
    (hani_moved, "16 features"),
    (mark_in_dist, "17 shapes"),
    (dist_stacked, "17 shapes"),
    (jan_twice, "16 features"),
]


def failing(path):
    r = verify_j.Report("mutant")
    cases = json.loads((verify_j.DATA / "cases.json").read_text())
    j, base = TTFont(path), TTFont(verify_j.face_path(SIZE, W))
    face = verify_j.Face(path)
    r.guarded("15 CJK widths", lambda: verify_j.check_widths(r, W, cases, face))
    r.guarded("16 features", lambda: verify_j.check_features(r, j, base, cases))
    build = json.loads((verify_j.DATA / "build.json").read_text())[str(W)]
    shapes = json.loads((verify_j.DATA / "shapes.json").read_text())
    r.guarded("17 shapes", lambda: verify_j.check_shapes(r, SIZE, W, j, build, shapes, cases))
    return {f.split(" ", 1)[1] for f in r.failed}


def main():
    # Every mutation is made to a face that passes both checks, or a catch would mean nothing
    if failing(verify_j.j_path(SIZE, W)):
        print("J Text Regular fails before any mutation")
        return 1
    missed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for mutate, expect in MUTATIONS:
            font = TTFont(verify_j.j_path(SIZE, W))
            mutate(font)
            path = Path(tmp) / f"{mutate.__name__}.ttf"
            font.save(path)
            caught = expect in failing(path)
            missed += not caught
            print(f"{'CAUGHT' if caught else 'MISSED'} {mutate.__name__}: {expect}", flush=True)
    print("mutations:", "FAIL" if missed else "PASS")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
