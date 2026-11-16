# SPDX-License-Identifier: Apache-2.0
"""Measure which installed face Windows draws each of Harena UI J's chunks with, and that face's line
metrics; write data/v0_6/fallback.json.

Names, glyph counts and numbers only come back. In Edge under a Segoe stack, DevTools reports the
platform faces a text was drawn with: per face and chunk under no language, `ko` and `ja`, and per
character under no language for the Text faces. The chosen face for a chunk and weight is the one that
draws most of its characters with no language. metrics.ps1 reads that face's metrics from its file on
the guest. Then J Text, declared with those metrics as overrides, must give the Segoe stack's line box
at 9-96 px for a line of the characters the chosen face draws.

Usage: python probe/v0_6/run.py <cdp-http-base> <repo-root-url> <metrics.json from metrics.ps1> <provenance.json> [--reuse]
With a metrics file lacking a chosen face, it prints the faces to read and exits 1; --reuse then keeps
the faces measured, if the cases and the browser are the same.
"""
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build import SIZES, WEIGHTS, face_path  # noqa: E402
from build_j import face_path_j  # noqa: E402
from build_web import chunks  # noqa: E402

LANGS = ("", "ko", "ja")


def overrides(face):
    """A fallback face's line metrics as Edge takes them on Windows, from DirectWrite: win ascent and
    descent, and the gap hhea adds beyond them; as CSS percentages of the em."""
    upem, (ascent, descent, gap), (win_ascent, win_descent) = face["upem"], face["hhea"], face["win"]
    extra = max(0, ascent - descent + gap - win_ascent - win_descent)
    return {"ascent-override": 100 * win_ascent / upem, "descent-override": 100 * win_descent / upem,
            "line-gap-override": 100 * extra / upem}
LINE_SIZES = list(range(9, 97))
SAMPLE = 40  # characters per line in the line box check
WORK = ROOT / "build/v0_6"
REUSE = "--reuse" in sys.argv


def stack(size):
    return f'"Segoe UI Variable {size}", "Segoe UI"'


def drawn(cdp, base, cases, name):
    path = WORK / f"{name}.json"
    path.write_text(json.dumps({"cases": cases}))
    res = subprocess.run(["node", str(ROOT / "probe/v0_6/fallback.mjs"), cdp, f"{base}/probe/page.html", str(path)],
                         capture_output=True, text=True, timeout=3600, check=True)
    return json.loads(res.stdout)


def main():
    cdp, base, metrics_path, prov_path = [a for a in sys.argv[1:] if a != "--reuse"][:4]
    WORK.mkdir(parents=True, exist_ok=True)
    table = {}
    for size in SIZES:
        for w in WEIGHTS:
            table[size, w] = chunks(TTFont(face_path_j(size, w), lazy=True).getBestCmap(),
                                    TTFont(face_path(size, w), lazy=True).getBestCmap())
    # The chunk table is the same in every face (build_web's rule reads only the code points).
    names = list(table["Text", 400])
    assert all(t == table["Text", 400] for t in table.values()), "chunks differ between faces"

    cases = [{"key": f"{size}|{w}|{name}|{lang}", "family": stack(size), "weight": w, "lang": lang,
              "text": "".join(map(chr, table[size, w][name]))}
             for size, w in table for name in names for lang in LANGS]
    char_cases = [{"key": f"{w}|{c:04X}", "family": stack("Text"), "weight": w, "lang": "", "text": chr(c)}
                  for w in WEIGHTS for name in names for c in table["Text", w][name]]
    # A previous run's faces are reused only when asked, and only for the same cases in the same browser.
    browser = json.loads(subprocess.run(["curl", "-s", f"{cdp}/json/version"], capture_output=True, text=True,
                                        check=True).stdout)["Browser"]
    # The guest by its provenance, its fonts by the files metrics.ps1 read, the probe by its own bytes.
    fonts = sorted((k, v.get("sha256")) for k, v in
                   json.loads(Path(metrics_path).read_text(encoding="utf-8-sig")).items() if v)
    fingerprint = hashlib.sha256(json.dumps([browser, Path(prov_path).read_text(), fonts, cases, char_cases,
                                             (ROOT / "probe/v0_6/fallback.mjs").read_text()]).encode()).hexdigest()
    cache = WORK / "drawn.json"
    kept = json.loads(cache.read_text()) if REUSE and cache.exists() else {}
    def drawn_ok(entry):  # what fallback.mjs prints for one case: [family, postScriptName, glyphs], at least one
        return isinstance(entry, list) and entry and all(
            isinstance(f, list) and len(f) == 3 and isinstance(f[0], str) and isinstance(f[1], str)
            and isinstance(f[2], int) for f in entry)

    valid = (isinstance(kept, dict) and kept.get("fingerprint") == fingerprint
             and isinstance(kept.get("faces"), dict) and isinstance(kept.get("chars"), dict)
             and all(drawn_ok(kept["faces"].get(c["key"])) for c in cases)
             and all(drawn_ok(kept["chars"].get(c["key"])) for c in char_cases))
    if valid:
        faces, per_char = kept["faces"], kept["chars"]
    else:
        faces = drawn(cdp, base, cases, "chunks")
        per_char = drawn(cdp, base, char_cases, "chars")
        cache.write_text(json.dumps({"fingerprint": fingerprint, "faces": faces, "chars": per_char}))

    out_chunks, chosen = {}, set()
    for name in names:
        out_chunks[name] = {}
        for w in WEIGHTS:
            by_size = {}
            for size in SIZES:
                by_size[size] = {lang: sorted(([ps, n] for _, ps, n in faces[f"{size}|{w}|{name}|{lang}"]),
                                              key=lambda r: -r[1]) for lang in LANGS}
            first = by_size["Text"]
            assert all(v == first for v in by_size.values()), f"{name} {w}: optical sizes fall back differently"
            face = first[""][0][0]
            chosen.add(face)
            out_chunks[name][str(w)] = {"face": face, "drawn": first}

    metrics = json.loads(Path(metrics_path).read_text(encoding="utf-8-sig"))
    missing = sorted(f for f in chosen if not metrics.get(f))
    if missing:
        print("read these faces with metrics.ps1:", ",".join(missing))
        return 1

    # Per character, with no language: the ones a face other than their chunk's draws.
    others, lines = {}, {}
    line_cases = []
    for w in WEIGHTS:
        others[str(w)] = {}
        for name in names:
            face = out_chunks[name][str(w)]["face"]
            mine = []
            for c in table["Text", w][name]:
                got = [ps for _, ps, _ in per_char[f"{w}|{c:04X}"]]
                if got == [face]:
                    mine.append(c)
                else:
                    others[str(w)][f"{c:04X}"] = got
            line_cases.append({"key": f"{name} {w}", "weight": w, "lang": "",
                               "font": f"{base}/dist/HarenaUIJ-Text{WEIGHTS[w]}.ttf",
                               "overrides": overrides(metrics[face]),
                               "text": "".join(map(chr, mine[::max(1, len(mine) // SAMPLE)][:SAMPLE]))})
    expr = WORK / "lines-expr.js"
    expr.write_text(f"const CONFIG = {json.dumps({'cases': line_cases, 'sizes': LINE_SIZES, 'stack': stack('Text')})};\n"
                    + (ROOT / "probe/v0_6/lines.js").read_text())
    res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(expr), "1200"],
                         capture_output=True, text=True, timeout=1300, check=True)
    lines = json.loads(res.stdout)
    bad = {k: v for k, v in lines.items() if v}
    counts = {w: Counter(" ".join(v) for v in o.values()) for w, o in others.items()}
    print("chosen:", {n: {w: v["face"] for w, v in d.items()} for n, d in out_chunks.items()})
    print("drawn by another face, no language:", {w: sum(c.values()) for w, c in counts.items()})
    print("line boxes differing:", bad or "none")

    provenance = json.loads(Path(prov_path).read_text())
    provenance["method"] = ("faces from DevTools' CSS.getPlatformFontsForNode under a Segoe stack, per face and "
                            "chunk and, for the Text faces with no language, per character; metrics from each "
                            "face's file on the guest (probe/v0_6/metrics.ps1); checked by line box height at "
                            "9-96 px with J Text declaring them as overrides")
    data = {"provenance": provenance,
            "faces": {f: metrics[f] for f in sorted(chosen)},
            "chunks": out_chunks,
            "others": others}
    (ROOT / "data/v0_6").mkdir(exist_ok=True)
    (ROOT / "data/v0_6/fallback.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
