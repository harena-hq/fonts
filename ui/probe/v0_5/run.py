# SPDX-License-Identifier: Apache-2.0
"""Measure Segoe Fluent Icons' geometry; write data/v0_5/segoe-icons.json.

Numbers only come back: per code point its advance, ink box and glyph group, read from the
file by font.ps1 on the guest, then checked here against what Edge lays out and inks. The
controls U+0000 and U+000D are read from the file but cannot be laid out alone.

Usage: python probe/v0_5/run.py <cdp-http-base> <repo-root-url> <font.json from font.ps1> <provenance.json>
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAMILY = "Segoe Fluent Icons"
CONTROLS = {"0000", "000D"}
SIZES = [12, 14, 16, 20, 28, 40, 1000]
INK_TOLERANCE = 16  # font units, two pixels at 256 px: pixel edges, not the outline's


def main():
    cdp, base, font_path, prov_path = sys.argv[1:5]
    font = json.loads(Path(font_path).read_text(encoding="utf-8-sig"))
    rows = font.pop("points")
    points = [r[0] for r in rows if r[0] not in CONTROLS]
    expr = f"const CONFIG = {json.dumps({'family': FAMILY, 'points': points, 'sizes': SIZES})};\n"
    expr += (ROOT / "probe/v0_5/geometry.js").read_text()
    tmp = ROOT / "build/v0_5-expr.js"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(expr)
    res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(tmp), "300"],
                         capture_output=True, text=True, timeout=320, check=True)
    edge = json.loads(res.stdout)

    bad = []
    for point, _, advance, box in rows:
        if point in CONTROLS:
            continue
        width, ink = edge["out"][point]
        if abs(width - advance) > 0.02:
            bad.append((point, "width", width, advance))
        if bool(box) != bool(ink) or box and any(abs(a - b) > INK_TOLERANCE for a, b in zip(ink, box)):
            bad.append((point, "ink", ink, box))
    for size, height in edge["heights"].items():
        if height != int(size):
            bad.append((size, "height", height))
    if bad:
        sys.exit(f"{len(bad)} disagree between the file and Edge, first: {bad[:8]}")

    doc = {
        "provenance": {**json.loads(Path(prov_path).read_text()), "segoe_fluent_icons": {
            "file": "SegoeIcons.ttf", "sha256": font.pop("sha256"), "version": font.pop("version")},
            "method": "advances and ink boxes from the file's hmtx and glyf headers on the guest; "
                      "checked against DOM width at 2048 px and pixel edges at 256 px in Edge"},
        "unit": "font units, 2048 per em",
        "columns": ["point", "group", "advance", "ink [xMin, xMax, yMin, yMax] or null"],
        **font,
        "line_height_em": 1,
        "points": rows,
    }
    (ROOT / "data/v0_5").mkdir(exist_ok=True)
    out = json.dumps(doc, indent=0, sort_keys=True).replace(",\n", ",").replace("[\n", "[").replace("\n]", "]")
    (ROOT / "data/v0_5/segoe-icons.json").write_text(out + "\n")
    print(len(rows), "points", len({r[1] for r in rows}), "groups", sum(r[3] is None for r in rows), "no ink")


if __name__ == "__main__":
    main()
