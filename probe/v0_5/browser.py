# SPDX-License-Identifier: Apache-2.0
"""Harena UI Icons against Segoe Fluent Icons in Edge: every point, size and style, text and icons
together under a stack, and each glyph against the SVG it came from, which Edge parses independently
of the build. Exits non-zero on any difference. U+0000 and U+000D cannot be laid out alone: 2 left out.

Usage: python probe/v0_5/browser.py <cdp-http-base> <repo-root-url>
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIZES = [12, 14, 16, 20, 28, 40, 1000]
STYLES = [{"css": f"font-weight:{w};font-style:{s}", "canvas": f"{s} {w}"}
          for w, s in ((300, "normal"), (400, "normal"), (600, "normal"), (700, "normal"), (400, "italic"), (700, "italic"))]
CONTROLS = {"0000", "000D"}
STRINGS = ["\uE700\uE713\uE721", "\uE844\uE9B4\uF1D4", "\uE843 \uEB1A \uF47F", "\uE713 Settings", "Save \uE74E as",
           "\uE721 Search the Web \uE711", "File\uE70D  Edit\uE70D  View\uE70D"]
FIDELITY = 0.96  # a glyph against its source SVG, inked to 64 px
SMALL_BOX = {"E7A5"}  # Segoe's box for it is a sliver: too few pixels at this size to compare
SLICE = 400


def main():
    cdp, base = sys.argv[1:3]
    points = [p[0] for p in json.loads((ROOT / "data/v0_5/segoe-icons.json").read_text())["points"] if p[0] not in CONTROLS]
    script = (ROOT / "probe/v0_5/browser.js").read_text()
    tmp = ROOT / "build/v0_5/browser-expr.js"
    measured, off, offs, differs, heights, strings = 0, 0, [], [], {}, []
    for i in range(0, len(points), SLICE):
        config = {"font": f"{base}/dist/HarenaUIIcons-Regular.ttf", "points": points[i:i + SLICE], "sizes": SIZES,
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
    rows = [{"point": r["points"][0], "icon": r["icon"]} for r in json.loads((ROOT / "data/icons/table.json").read_text())["rows"]
            if r["kind"] == "fluent" and not r.get("rotate")]
    source = (ROOT / "probe/v0_5/fidelity.js").read_text()
    scores = {}
    for i in range(0, len(rows), 150):
        config = {"font": f"{base}/dist/HarenaUIIcons-Regular.ttf", "url": "/build/v0_5/fluent.json", "rows": rows[i:i + 150]}
        tmp.write_text(f"const CONFIG = {json.dumps(config)};\n" + source)
        res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(tmp), "100"],
                             capture_output=True, text=True, timeout=120, check=True)
        scores.update(json.loads(res.stdout))
    unlike = sorted((v, k) for k, v in scores.items() if v < FIDELITY and k not in SMALL_BOX)
    print("glyphs against their SVG:", len(scores), "under", FIDELITY, unlike[:10])
    sys.exit(1 if off or bad_lines or bad_strings or differs or unlike else 0)


if __name__ == "__main__":
    main()
