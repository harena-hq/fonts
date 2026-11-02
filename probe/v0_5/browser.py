# SPDX-License-Identifier: Apache-2.0
"""Harena UI Icons against Segoe Fluent Icons in Edge: every point, size and style, text and icons
together under a stack, and each inked glyph against its sources, drawn by Edge independently of the
build. Exits non-zero on any difference. U+0000 and U+000D cannot be laid out alone: 2 left out.

Usage: python probe/v0_5/browser.py <cdp-http-base> <repo-root-url>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_icons import BADGES, PLACEHOLDER, SYMBOLS, TEXT_FACES  # noqa: E402

SIZES = [12, 14, 16, 20, 28, 40, 1000]
STYLES = [{"css": f"font-weight:{w};font-style:{s}", "canvas": f"{s} {w}"}
          for w, s in ((300, "normal"), (400, "normal"), (600, "normal"), (700, "normal"), (400, "italic"), (700, "italic"))]
CONTROLS = {"0000", "000D"}
STRINGS = ["\uE700\uE713\uE721", "\uE844\uE9B4\uF1D4", "\uE843 \uEB1A \uF47F", "\uE713 Settings", "Save \uE74E as",
           "\uE721 Search the Web \uE711", "File\uE70D  Edit\uE70D  View\uE70D"]
FIDELITY = 0.96  # a glyph against its sources, inked to 64 px
SMALL_BOX = {"E7A5"}  # Segoe's box for it is a sliver: too few pixels at this size to compare
SLICE = 400


def main():
    cdp, base = sys.argv[1:3]
    # Edge keeps a font by its URL: the hash makes it load the bytes on disk, not an earlier build's.
    built = f"{base}/dist/HarenaUIIcons-Regular.ttf?{hashlib.sha256((ROOT / 'dist/HarenaUIIcons-Regular.ttf').read_bytes()).hexdigest()}"
    points = [p[0] for p in json.loads((ROOT / "data/v0_5/segoe-icons.json").read_text())["points"] if p[0] not in CONTROLS]
    script = (ROOT / "probe/v0_5/browser.js").read_text()
    tmp = ROOT / "build/v0_5/browser-expr.js"
    measured, off, offs, differs, heights, strings = 0, 0, [], [], {}, []
    for i in range(0, len(points), SLICE):
        config = {"font": built, "points": points[i:i + SLICE], "sizes": SIZES,
                  "styles": STYLES, "strings": STRINGS,
                  "text": f"{base}/dist/HarenaUI-TextRegular.ttf"}
        tmp.write_text(f"const CONFIG = {json.dumps(config)};\n" + script)
        res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(tmp), "280"],
                             capture_output=True, text=True, timeout=300, check=True)
        out = json.loads(res.stdout)
        measured += out["measured"]
        off += out["offCount"]
        offs += out["off"]
        differs += out["differs"]
        heights, strings = out["heights"], out["strings"]
        print(i + SLICE, measured, off, flush=True)
    bad_lines = {k: v for k, v in heights.items() if v[0] != v[1]}
    bad_strings = [s for s in strings if abs(s[2][0] - s[3][0]) > 1 / 64 + 1e-6 or s[2][1] != s[3][1]]
    print("measured", measured, "outside", off, offs[:8])
    print("line boxes", heights, "differ:", bad_lines)
    print("strings", strings, "differ:", bad_strings)
    print("stack draws other than Segoe:", len(differs), differs[:10])
    table = json.loads((ROOT / "data/icons/table.json").read_text())["rows"]
    by_point = {r["points"][0]: r for r in table}
    def reference(r):
        out = {"point": r["points"][0], "kind": r["kind"]}
        for key in ("icon", "rotate", "text", "weight", "level"):
            if key in r:
                out[key] = r[key]
        if r["kind"] == "none":
            out["icon"] = PLACEHOLDER
        if r["kind"] == "compose":
            out["badge"] = f"{BADGES.get(r['badge'], r['badge'])}_16_filled"
        if r["kind"] == "mirror":
            out["of"] = reference(by_point[r["of"]])
        return out
    rows = [reference(r) for r in table if r["kind"] != "blank"]
    source = (ROOT / "probe/v0_5/fidelity.js").read_text()
    def fidelity(chunk):
        scores = {}
        for i in range(0, len(chunk), 150):
            config = {"font": built, "url": "/build/v0_5/fluent.json",
                      "faces": {k: f"{base}/dist/HarenaUIJ-Text{v}.ttf" for k, v in TEXT_FACES.items()},
                      "symbols": f"{base}/{SYMBOLS.relative_to(ROOT)}", "rows": chunk[i:i + 150]}
            tmp.write_text(f"const CONFIG = {json.dumps(config)};\n" + source)
            res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(tmp), "100"],
                                 capture_output=True, text=True, timeout=120, check=True)
            scores.update(json.loads(res.stdout))
        return scores
    scores = fidelity(rows)
    # The comparison has to be able to fail: each kind against the next kind's drawing, and each recipe undone.
    kinds = {}
    for r in rows:
        kinds.setdefault(r["kind"], []).append(r)
    order = list(kinds)
    swapped = [{**kinds[order[(i + 1) % len(order)]][0], "point": kinds[k][0]["point"]} for i, k in enumerate(order)]
    turned = next(r for r in rows if r.get("rotate"))
    badged = kinds["compose"][0]
    undone = [{k: v for k, v in turned.items() if k != "rotate"}, 
              {"point": badged["point"], "kind": "fluent", "icon": badged["icon"]},
              {"point": kinds["holes"][0]["point"], "kind": "fluent", "icon": kinds["holes"][0]["icon"]},
              {**kinds["bars"][0], "level": 4}]  # ZeroBars drawn full
    blind = [(r["point"], score) for r in swapped + undone for score in fidelity([r]).values() if score >= FIDELITY]
    # Some mirrors are symmetric, so one flipped drawing that differs is what shows the check can see a flip.
    unflipped = fidelity([{**r["of"], "point": r["point"]} for r in kinds["mirror"]])
    if min(unflipped.values()) >= FIDELITY:
        blind.append(("mirror", min(unflipped.values())))
    print("wrong drawings that pass:", blind)
    unlike = sorted((v, k) for k, v in scores.items() if v < FIDELITY and k not in SMALL_BOX)
    print("glyphs against their sources:", len(scores), "under", FIDELITY, unlike[:20])
    sys.exit(1 if off or bad_lines or bad_strings or differs or unlike or blind else 0)


if __name__ == "__main__":
    main()
