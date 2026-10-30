# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""The v0.1 gate. Each check in PLAN.md's v0.1 Done-when prints one line; any
failure, including an error inside a check, makes the exit status non-zero.
The last line is `gate: PASS` or `gate: FAIL`.

The gate does not take its expectations from scripts/build.py. The values the
spec fixes are written here, the Open Sans reference is instanced and
decomposed here, and the overlap criterion is computed here. What it reads from
the build is the font, and data/v0_1/build.json (the chosen point and the
ligature copies), whose claims it checks rather than trusts. It writes its
compiled Open Sans reference to build/verify-reference.ttf for shaping.

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
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "dist/HarenaUI-TextRegular.ttf"
OPEN_SANS = ROOT / "sources/opensans/OpenSans[wdth,wght].ttf"
SEGOE = ROOT / "data/v0_1/segoe-ui-variable.json"
STEMS = ROOT / "data/v0/stems.json"
POINT = ROOT / "data/v0_1/build.json"
TNUM = ROOT / "data/v0_1/segoe-tnum.json"
ALLOW = ROOT / "data/v0_1/overlaps.json"
STRINGS = ROOT / "probe/v0/strings.json"
INSTANCE = "Segoe UI Variable Text|400"

# PLAN.md v0.1, scope items 5 and 6, written out rather than imported.
UPM = 2048
PX = UPM / 1000
METRICS = {"hhea.ascent": 2210, "hhea.descent": -514, "hhea.lineGap": 0,
           "OS/2.sTypoAscender": 1491, "OS/2.sTypoDescender": -431, "OS/2.sTypoLineGap": 269,
           "OS/2.usWinAscent": 2210, "OS/2.usWinDescent": 514}
NAMES = {
    0: "Copyright 2020 The Open Sans Project Authors (https://github.com/googlefonts/opensans)\n"
       "Copyright 2026 Jeeyong Um",
    1: "Harena UI Text", 2: "Regular", 3: "0.1.0;HRNA;HarenaUIText-Regular",
    4: "Harena UI Text Regular", 5: "Version 0.1.0", 6: "HarenaUIText-Regular",
    13: "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
        "This license is available with a FAQ at: https://openfontlicense.org",
    14: "https://openfontlicense.org", 16: "Harena UI", 17: "Text",
}
FORBIDDEN = ("segoe", "selawik", "source", "pretendard")
# Scope item 2's point: stems equal, median ink width equal. Tolerances cover
# rounding wght to an integer and wdth to 0.1.
STEM_TOL_PX, INK_RATIO_TOL = 0.3, 0.005

failed = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))
    if not ok:
        failed.append(name)


def guarded(name, fn):
    try:
        fn()
    except Exception as e:  # a check that cannot run has failed
        check(name, False, f"error: {e!r}")


REF_PATH = ROOT / "build/verify-reference.ttf"


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

    def width(text):
        return sum(p.x_advance for _, p in shape(text))

    def shape(text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {"kern": True})
        return list(zip(buf.glyph_infos, buf.glyph_positions))
    width.shape = shape
    return width


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
    hashes = []
    for _ in range(2):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/build.py")], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"build failed: {r.stderr.strip().splitlines()[-1:]}")
        hashes.append(hashlib.sha256(FONT.read_bytes()).hexdigest())

    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).returncode

    committed = all(git("cat-file", "-e", f"HEAD:{p}") == 0 for p in ("SHA256SUMS", "data/v0_1/build.json"))
    same_as_head = git("diff", "--quiet", "HEAD", "--", "SHA256SUMS", "data/v0_1/build.json") == 0
    listed = (ROOT / "SHA256SUMS").read_text().split()[0] == hashes[0]
    check("8 reproducible", hashes[0] == hashes[1] and committed and same_as_head and listed,
          f"two builds {'identical' if hashes[0] == hashes[1] else 'differ'}; "
          + ("not committed" if not committed else
             "SHA256SUMS and build.json equal HEAD's" if same_as_head else "differ from HEAD"))


def main():
    if "--no-rebuild" in sys.argv:
        print("SKIP 8 reproducible: --no-rebuild")
    else:
        guarded("8 reproducible", reproducible)

    try:
        doc = json.loads(SEGOE.read_text())
        target, seg = doc["target"], doc["instances"][INSTANCE]
        point = json.loads(POINT.read_text())
        font = TTFont(FONT)
        ref = compiled(instantiateVariableFont(
            TTFont(OPEN_SANS), {"wght": point["wght"], "wdth": point["wdth"]}, updateFontNames=False))
        cmap, rcmap, hmtx = font.getBestCmap(), ref.getBestCmap(), font["hmtx"]
        REF_PATH.parent.mkdir(exist_ok=True)
        REF_PATH.write_bytes(_bytes(ref))
        copies = point["copies"]
        width = shaper(FONT)
    except Exception as e:
        check("inputs", False, f"error: {e!r}")
        print("gate: FAIL")
        sys.exit(1)

    def c1():
        bad = [cp for cp in target if cp not in cmap
               or abs(hmtx[cmap[cp]][0] - seg["advance"][str(cp)] * PX) > 0.5]
        targets = {cmap[cp] for cp in target if cp in cmap}
        rest = [g for g in ref.getGlyphOrder() if g not in targets]
        others = [g for g in rest if g not in hmtx.metrics or hmtx[g][0] != ref["hmtx"][g][0]]
        check("1 advances", not bad and not others,
              f"{len(target) - len(bad)}/{len(target)} target glyphs at Segoe's advance; "
              f"{len(rest) - len(others)}/{len(rest)} others at Open Sans'"
              + (f"; off: {''.join(chr(c) for c in bad[:20])}" if bad else "")
              + (f"; others changed: {others[:10]}" if others else ""))
    guarded("1 advances", c1)

    def c2():
        letters = doc["kern_pairs_from"]
        adv = {cp: seg["advance"][str(cp)] for cp in letters}
        kern = seg["kern"]
        bad, kerned, plain = [], 0, 0
        for a in letters:
            for b in letters:
                k = kern.get(f"{a},{b}", 0.0)
                d = width(chr(a) + chr(b)) - (adv[a] + adv[b] + k) * PX
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
        check("2 kerning", not bad and not stray,
              f"{kerned} kerned and {plain} unkerned pairs and {runs} ligature runs within 0.5 units; "
              f"{len(stray) or 'no'} kern pairs beyond Segoe's"
              + ("; off, e.g. " + ", ".join(f"{chr(a)}{chr(b)} {d:+.1f}" for a, b, d in bad[:8]) if bad else "")
              + (f"; stray: {stray[:6]}" if stray else ""))
    guarded("2 kerning", c2)

    def c2t():
        tab = json.loads(TNUM.read_text())["tabular"]
        bad = []
        for key, px in tab.items():
            buf = hb.Buffer()
            buf.add_str(chr(int(key)))
            buf.guess_segment_properties()
            hb.shape(tnum_font, buf, {"tnum": True, "kern": True})
            got = sum(p.x_advance for p in buf.glyph_positions)
            if abs(got - px * PX) > 0.5:
                bad.append(f"{chr(int(key))} {got} vs {px * PX:.1f}")
        check("2t tabular digits", not bad, f"{len(tab) - len(bad)}/{len(tab)} digits at Segoe's tabular advance "
              "under tnum" + (f"; off: {bad}" if bad else ""))
    tnum_font = hb.Font(hb.Face(hb.Blob.from_file_path(str(FONT))))
    guarded("2t tabular digits", c2t)

    def c3():
        strings = [s for g in json.loads(STRINGS.read_text()).values() for s in g]
        errs = [(s, (width(s) / PX - seg["strings"][s][0]) / seg["strings"][s][0]) for s in strings]
        worst = max(errs, key=lambda e: abs(e[1]))
        check("3 strings", abs(worst[1]) <= 0.001,
              f"{len(strings)} strings, worst {100 * worst[1]:+.3f}% ({worst[0]!r})")
    guarded("3 strings", c3)

    def c4():
        got = {k: getattr(font[k.split(".")[0]], k.split(".")[1]) for k in METRICS}
        off = [f"{k} {got[k]}" for k in METRICS if got[k] != METRICS[k]]
        if font["OS/2"].fsSelection & (1 << 7):
            off.append("USE_TYPO_METRICS set")
        if font["head"].unitsPerEm != UPM:
            off.append(f"unitsPerEm {font['head'].unitsPerEm}")
        check("4 vertical metrics", not off, "as specified" if not off else f"differ: {off}")
    guarded("4 vertical metrics", c4)

    def c5():
        bad = []
        # The chosen point satisfies scope item 2, measured here.
        target_stem = json.loads(STEMS.read_text())["stems"][INSTANCE]["l"]
        lo, hi = ink_x(ref, rcmap[ord("l")])
        stem = (hi - lo) / PX
        ratios = []
        for cp in target:
            row, b = seg["ink"].get(str(cp)), ink_x(ref, rcmap[cp])
            if row and b and b[1] > b[0]:
                ratios.append((row[1] - row[0]) / ((b[1] - b[0]) / PX))
        ratio = st.median(ratios)
        if abs(stem - target_stem) > STEM_TOL_PX:
            bad.append(f"stem {stem:.2f} px against {target_stem}")
        if abs(ratio - 1) > INK_RATIO_TOL:
            bad.append(f"median ink ratio {ratio:.4f}")
        if cmap != rcmap:
            diff = sorted(set(cmap.items()) ^ set(rcmap.items()))
            bad.append(f"cmap differs from Open Sans': {diff[:6]}")
        order = font.getGlyphOrder()
        n_ref = len(ref.getGlyphOrder())
        if order[:n_ref] != ref.getGlyphOrder() or set(order[n_ref:]) != set(copies):
            bad.append("glyph order is not Open Sans' plus the ligature copies")
        rset = set(ref.getGlyphOrder())
        dxs = {}
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
        check("5 outlines", not bad,
              f"{n - len(bad)}/{n} glyphs equal Open Sans at wght {point['wght']}, wdth {point['wdth']} "
              f"({len(copies)} copies), ink placed per the sidebearing split; stem {stem:.2f}/{target_stem} px, ink ratio {ratio:.4f}"
              + (f"; differ: {bad[:8]}" if bad else ""))
    guarded("5 outlines", c5)

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
        check("5b marks", not bad, f"{n - len(bad)}/{n} base+mark clusters place the mark as Open Sans does "
              "relative to the base's ink" + (f"; differ: {bad[:4]}" if bad else ""))
    guarded("5b marks", c5b)

    def c6():
        recs = sorted((r.platformID, r.platEncID, r.langID, r.nameID, r.toUnicode()) for r in font["name"].names)
        want = sorted((3, 1, 0x409, nid, v) for nid, v in NAMES.items())
        hits = [(r[3], w) for r in recs for w in FORBIDDEN if w in r[4].lower()]
        check("6 names", recs == want and not hits,
              "as specified" if recs == want and not hits else
              f"extra {[r[:4] for r in recs if r not in want]}, missing {[r[:4] for r in want if r not in recs]}, "
              f"forbidden {hits}")
    guarded("6 names", c6)

    def c7():
        allowed = set(json.loads(ALLOW.read_text())["code_points"])
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
        check("7 overlaps", not new and not stale, f"{len(found)} found, all listed"
              + (f"; not listed: {''.join(chr(c) for c in sorted(new))}" if new else "")
              + (f"; listed but gone: {''.join(chr(c) for c in sorted(stale))}" if stale else ""))
    guarded("7 overlaps", c7)

    print("gate:", "FAIL" if failed else "PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
