#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""The web delivery's gate: the stylesheets and WOFF2 files lay text out as the built TTFs do.

W1 resolving each family as a browser does, every code point of its TTF draws from exactly one file,
   which holds its chunk inside its declared range, with the TTF's glyphs, advances and metrics;
   J's Latin is Harena UI's file, glyph for glyph, and no chunk's range takes in a Latin code point.
W2 no group of glyphs that a GSUB or GPOS rule of a J face ties together spans two files.
W3 every string of the v0.3 and v0.4 cases, itemized into script runs, each run shaped with HarfBuzz
   under each language by the whole TTF, positions as its pieces shaped by the files that draw them.
W4 every face is declared as locked: family, weight range, upright, block, and a chunk's line
   metrics those of its fallback face in data/v0_6/fallback.json.
W5 the stylesheets are what build_css.py writes, SHA256SUMS-Web lists exactly dist/web, and the
   package assembles, packs exactly its declared files and resolves every export.

Usage: python scripts/verify_web.py
"""
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.recordingPen import RecordingPen
from fontTools import unicodedata
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_css  # noqa: E402
from build import ROOT, SIZES, WEIGHTS, face_path  # noqa: E402
from build_j import face_path_j  # noqa: E402
from build_web import ICONS, WEB, chunks, j_file, overrides, ui_file  # noqa: E402

NPM = ROOT / "npm"
LANGS = ("", "ko", "ja")
FACE = re.compile(r"@font-face \{(.*?)\}", re.S)
PROPERTY = re.compile(r"^\s*([a-z-]+): (.*);$", re.M)


def parse(css):
    faces = []
    for body in FACE.findall(css):
        props = dict(PROPERTY.findall(body))
        spans = []
        for part in props.pop("unicode-range").split(", "):
            a, _, b = part[2:].partition("-")
            spans.append((int(a, 16), int(b or a, 16)))
        props["points"] = {c for a, b in spans for c in range(a, b + 1)}
        props["file"] = re.fullmatch(r'url\("\./fonts/([^"]+)"\) format\("woff2"\)', props.pop("src")).group(1)
        props["font-family"] = props["font-family"].strip('"')
        faces.append(props)
    return faces


def families(npm):
    """{(family, weight): [declared face, ...]} over the three stylesheets, and the faces in order."""
    out, every = {}, []
    for name in ("ui.css", "j.css", "icons.css"):
        for f in parse((npm / name).read_text()):
            f["sheet"] = name
            out.setdefault((f["font-family"], f["font-weight"]), []).append(f)
            every.append(f)
    return out, every


def outline(font, gname):
    pen = RecordingPen()
    font.getGlyphSet()[gname].draw(pen)
    return pen.value, font["hmtx"][gname][0]


def ttf_of(family, w):
    if family == "Harena UI Icons":
        return ICONS
    size = family.rsplit(" ", 1)[1]
    return face_path_j(size, w) if family.startswith("Harena UI J ") else face_path(size, w)


def groups(font):
    """Sets of code points that some GSUB or GPOS rule of the font reads together."""
    order = font.getGlyphOrder()
    parent = {g: g for g in order}

    def find(g):
        while parent[g] != g:
            parent[g] = parent[parent[g]]
            g = parent[g]
        return g

    def tie(gs):
        gs = list(gs)
        for g in gs[1:]:
            parent[find(g)] = find(gs[0])

    def cov(c):
        return list(c.glyphs) if c is not None else []

    def context(st):
        gs = []
        for attr in ("Coverage", "BacktrackCoverage", "InputCoverage", "LookAheadCoverage"):
            value = getattr(st, attr, None)
            for c in value if isinstance(value, list) else [value]:
                gs += cov(c)
        for attr in ("ClassDef", "BacktrackClassDef", "InputClassDef", "LookAheadClassDef"):
            if getattr(st, attr, None) is not None:
                gs += list(getattr(st, attr).classDefs)
        for attr in ("ChainSubRuleSet", "ChainPosRuleSet", "SubRuleSet", "PosRuleSet"):
            for rs in getattr(st, attr, None) or []:
                for r in (getattr(rs, attr[:-3], None) or []) if rs else []:
                    for seq in ("Backtrack", "Input", "LookAhead"):
                        gs += list(getattr(r, seq, None) or [])
        tie(gs)

    def gsub(st, kind):
        if kind == 7:
            return gsub(st.ExtSubTable, st.ExtensionLookupType)
        if kind == 1:
            for a, b in st.mapping.items():
                tie([a, b])
        elif kind in (2, 3):
            for a, b in (st.mapping if kind == 2 else st.alternates).items():
                tie([a, *b])
        elif kind == 4:
            for a, ligs in st.ligatures.items():
                for lig in ligs:
                    tie([a, *lig.Component, lig.LigGlyph])
        elif kind in (5, 6):
            context(st)

    def gpos(st, kind):
        if kind == 9:
            return gpos(st.ExtSubTable, st.ExtensionLookupType)
        if kind == 2 and st.Format == 1:
            for first, pairs in zip(cov(st.Coverage), st.PairSet):
                for r in pairs.PairValueRecord:
                    tie([first, r.SecondGlyph])
        elif kind == 2:
            # Format 2: a pair applies only if both glyphs are in the font, whatever its value
            tie(cov(st.Coverage) + list(st.ClassDef2.classDefs))
        elif kind in (4, 5, 6):
            mark = st.MarkCoverage if kind != 6 else st.Mark1Coverage
            base = {4: "BaseCoverage", 5: "LigatureCoverage", 6: "Mark2Coverage"}[kind]
            tie(cov(mark) + cov(getattr(st, base)))
        elif kind in (7, 8):
            context(st)

    for tag, walk in (("GSUB", gsub), ("GPOS", gpos)):
        if tag in font:
            for lookup in font[tag].table.LookupList.Lookup:
                for st in lookup.SubTable:
                    walk(st, lookup.LookupType)
    out = {}
    for c, g in font.getBestCmap().items():
        out.setdefault(find(g), set()).add(c)
    return [s for s in out.values() if len(s) > 1]


def strings():
    found = []

    def walk(v):
        if isinstance(v, str):
            found.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    for path in ("data/v0_3/cases.json", "data/v0_4/cases.json"):
        walk(json.loads((ROOT / path).read_text()))
    # Runs that open with punctuation whose scripts include kana, as no case does
    found += ["、あ", "「カタカナ」", "（ア）"]
    return sorted({s for s in found if s.strip()})


@lru_cache(maxsize=None)
def hb_font(data):
    return hb.Font(hb.Face(data))


def ttf_bytes(font):
    out = io.BytesIO()
    font.flavor = None
    font.save(out)
    return out.getvalue()


NEUTRAL = {"Zyyy", "Zinh", "Zzzz"}


def _scripts(ch):
    # Chromium's ScriptRunIterator shapes hiragana and katakana as one script, and keeps a run going
    # through a character whose script extensions include the run's script.
    return {"Kana" if s == "Hira" else s for s in unicodedata.script_extension(ch)}


def script_runs(text):
    """(ISO 15924 tag, text) runs as Chromium itemizes them: a run keeps the scripts all its characters
    allow, narrowing as each one comes, and ends at a character none of them allows; neutral
    characters join the run they are in."""
    runs = []
    for ch in text:
        scripts = _scripts(ch) - NEUTRAL
        if runs and (not scripts or runs[-1][0] & scripts or not runs[-1][0]):
            if scripts:
                runs[-1][0] = runs[-1][0] & scripts if runs[-1][0] else scripts
            runs[-1][1] += ch
        else:
            runs.append([scripts, ch])
    return [(min(s) if s else "Zyyy", t) for s, t in runs]


def shape(data, text, lang, script):
    buf = hb.Buffer()
    buf.add_str(text)
    if script != "Zyyy":
        buf.script = script
    if lang:
        buf.language = lang
    buf.guess_segment_properties()
    hb.shape(hb_font(data), buf, {})
    return [(p.x_advance, p.x_offset, p.y_offset) for p in buf.glyph_positions], buf.direction == "rtl"


def checks(web=WEB, npm=NPM):
    by_face, every = families(npm)
    files = {}

    # First, so that a damaged file is named before reading it can fail.
    listed = {}
    for line in (ROOT / "SHA256SUMS-Web").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        listed[Path(name).name] = digest
    present = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in web.glob("*.woff2")}
    yield "W5 SHA256SUMS-Web lists exactly dist/web", listed == present, f"{len(present)} files"

    def woff(name):
        if name not in files:
            files[name] = TTFont(web / name)
        return files[name]

    def weight_of(family, weight):
        if family == "Harena UI Icons":
            return 400
        # None for a range no Segoe instance answers to: W4 reports it, the others skip the face
        return next((k for k, v in build_css.weight_ranges().items() if "{} {}".format(*v) == weight), None)

    def drawn(faces):
        """{code point: file} as a browser resolves the family: the last declared face first, and a
        face draws a code point only if its range covers it and its file has it (CSS Fonts 4, 4.5)."""
        out = {}
        for f in faces:
            for c in set(woff(f["file"]).getBestCmap()) & f["points"]:
                out[c] = f["file"]
        return out

    # W1
    gaps, shared, held, glyphs, metrics, latin, taken = [], [], [], [], [], [], []
    for (family, weight), faces in sorted(by_face.items()):
        w = weight_of(family, weight)
        if w is None:
            continue
        ttf = TTFont(ttf_of(family, w))
        cmap = ttf.getBestCmap()
        where = drawn(faces)
        if set(where) != set(cmap):
            gaps.append(f"{family} {weight}: {len(set(cmap) - set(where))} drawn by no file, {len(set(where) - set(cmap))} extra")
        seen = {}
        if family.startswith("Harena UI J "):
            size = family.rsplit(" ", 1)[1]
            want = {j_file(size, w, n): set(p) for n, p in chunks(cmap, TTFont(face_path(size, w), lazy=True).getBestCmap()).items()}
            want[ui_file(size, w)] = set(TTFont(face_path(size, w), lazy=True).getBestCmap())
            latin_points = want[ui_file(size, w)]
            taken += [f["file"] for f in faces if f["file"] != ui_file(size, w) and f["points"] & latin_points]
        else:
            want = {f["file"]: set(cmap) for f in faces}
        for f in faces:
            font = woff(f["file"])
            fcmap = font.getBestCmap()
            for c in fcmap:
                if seen.setdefault(c, f["file"]) != f["file"]:
                    shared.append(f"{family} {weight} U+{c:04X}")
            if set(fcmap) != want.get(f["file"]) or not set(fcmap) <= f["points"]:
                held.append(f["file"])
            for table, attrs in (("head", ("unitsPerEm",)), ("hhea", ("ascent", "descent", "lineGap")),
                                 ("OS/2", ("sTypoAscender", "sTypoDescender", "sTypoLineGap", "usWinAscent", "usWinDescent"))):
                if any(getattr(font[table], a) != getattr(ttf[table], a) for a in attrs):
                    metrics.append(f"{f['file']} {table}")
            for c in sorted(set(fcmap) & set(cmap)):
                if outline(font, fcmap[c]) != outline(ttf, cmap[c]):
                    (latin if family.startswith("Harena UI J ") and f["file"].startswith("HarenaUI-") else glyphs).append(f"{f['file']} U+{c:04X}")
    yield "W1 every code point draws from a file, and only the TTF's", not gaps, "; ".join(gaps[:4])
    yield "W1 no code point is in two files", not shared, "; ".join(shared[:4])
    yield "W1 each file holds its chunk, inside its range", not held, "; ".join(held[:4])
    yield "W1 Latin text reaches no chunk", not taken, "; ".join(sorted(set(taken))[:4])
    yield "W1 each file's metrics are its TTF's", not metrics, "; ".join(metrics[:4])
    yield "W1 each file's glyphs are its TTF's", not glyphs, "; ".join(glyphs[:4])
    yield "W1 J's Latin is Harena UI's, glyph for glyph", not latin, "; ".join(latin[:4])

    # W2
    cut = []
    for size in SIZES:
        for w in WEIGHTS:
            where = drawn(by_face.get((f"Harena UI J {size}", "{} {}".format(*build_css.weight_ranges()[w])), []))
            for group in groups(TTFont(face_path_j(size, w))):
                spans = {where.get(c) for c in group}
                if len(spans) > 1:
                    cut.append(f"{size} {WEIGHTS[w]}: {len(group)} tied across {sorted(map(str, spans))}")
    yield "W2 no layout rule ties two files", not cut, "; ".join(cut[:3])

    # W3: a browser shapes each run of one script in one font. The whole TTF shapes the script run;
    # the files shape its pieces, and the pieces' positions must add up to the whole run's.
    texts, moved, decoded = strings(), [], {}
    for (family, weight), faces in sorted(by_face.items()):
        if family == "Harena UI Icons" or weight_of(family, weight) is None:
            continue
        whole = Path(ttf_of(family, weight_of(family, weight))).read_bytes()
        where = drawn(faces)
        for text in texts:
            for script, run in script_runs(text):
                pieces, last = [], object()
                for ch in run:
                    f = where.get(ord(ch))
                    if f != last:
                        pieces.append([f, ""])
                    pieces[-1][1] += ch
                    last = f
                if any(f is None for f, _ in pieces):
                    continue  # another family draws part of it
                for f, _ in pieces:
                    if f not in decoded:
                        decoded[f] = ttf_bytes(TTFont(web / f))
                for lang in LANGS:
                    want, rtl = shape(whole, run, lang, script)
                    got = [p for f, piece in (reversed(pieces) if rtl else pieces)
                           for p in shape(decoded[f], piece, lang, script)[0]]
                    if got != want:
                        moved.append(f"{family} {weight} {lang or '-'} {run!r}")
                        break
    yield "W3 split runs shape as the whole face", not moved, f"{len(texts)} strings; " + "; ".join(moved[:4])

    # W4
    ranges_want = {"{} {}".format(*v) for v in build_css.weight_ranges().values()}
    fallback = json.loads((ROOT / "data/v0_6/fallback.json").read_text())
    wrong = []
    for f in every:
        family, weight = f["font-family"], f["font-weight"]
        ok = f.get("font-style") == "normal" and f.get("font-display") == "block"
        if family == "Harena UI Icons":
            ok &= weight == "400" and f["sheet"] == "icons.css"
        else:
            ok &= weight in ranges_want and re.fullmatch(r"Harena UI (J )?(Small|Text|Display)", family) is not None
            ok &= f["sheet"] == ("j.css" if family.startswith("Harena UI J ") else "ui.css")
        chunk = re.fullmatch(r"HarenaUIJ-\w+?(Light|Semilight|Regular|Semibold|Bold)-(.+)\.woff2", f["file"])
        got = {k: float(f[k].rstrip("%")) for k in ("ascent-override", "descent-override", "line-gap-override") if k in f}
        if chunk:
            w = next(k for k, v in WEIGHTS.items() if v == chunk.group(1))
            entry = fallback["chunks"].get(chunk.group(2))
            want = overrides(fallback["faces"][entry[str(w)]["face"]]) if entry else None
            ok &= want is not None and set(got) == set(want) and all(abs(got[k] - want[k]) < 1e-6 for k in want)
        else:
            ok &= not got
        if not ok:
            wrong.append(f"{family} {weight} {f['file']}")
    yield "W4 faces are declared as locked", not wrong, f"{len(every)} faces; " + "; ".join(wrong[:4])

    # W5
    stale = [n for n, text in build_css.stylesheets().items() if (npm / n).read_text() != text]
    yield "W5 stylesheets are build_css.py's", not stale, " ".join(stale)
    named = {f["file"] for f in every}
    yield "W5 every declared file exists, and only those", named == set(present), \
        f"{len(named - set(present))} missing, {len(set(present) - named)} unused"

    if web != WEB or npm != NPM:
        return  # the package is assembled from the real tree only
    (ROOT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "build") as tmp:
        out = Path(tmp) / "package"
        built = subprocess.run([sys.executable, str(ROOT / "scripts/package_npm.py"), "--out", str(out)],
                               capture_output=True, text=True)
        yield "W5 the package assembles", built.returncode == 0, (built.stdout + built.stderr).strip()[-300:]
        if built.returncode:
            return
        pack = subprocess.run(["npm", "pack", "--dry-run", "--json"], cwd=out, capture_output=True, text=True)
        packed = {f["path"] for f in json.loads(pack.stdout)[0]["files"]} if pack.returncode == 0 else set()
        package = json.loads((out / "package.json").read_text())
        want = {"package.json"} | {f"fonts/{n}" for n in present}
        for entry in package["files"]:
            if not entry.endswith("/"):
                want.add(entry)
        want |= {str(p.relative_to(out)) for p in (out / "licenses").iterdir()}
        yield "W5 the tarball holds exactly the declared files", packed == want, \
            f"{len(packed)} files; {sorted(packed ^ want)[:4]}"
        exports = [v for k, v in package["exports"].items() if "*" not in k]
        yield "W5 every export resolves", all((out / e).is_file() for e in exports), " ".join(exports)


def main():
    failed = 0
    for name, ok, detail in checks():
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""), flush=True)
        failed += not ok
    print("gate:", "FAIL" if failed else "PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
