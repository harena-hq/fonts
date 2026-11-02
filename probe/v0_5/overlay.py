# SPDX-License-Identifier: Apache-2.0
"""Draw every table row, Segoe beside this font, under .private/v0_5/review/, with a key per row.

Usage: python probe/v0_5/overlay.py <cdp-http-base> <repo-root-url> <font path under the root> [points.json]
"""
import base64
import json
import subprocess
import sys

from stages import ROOT

PER_SHEET = 32
BATCH = 4


def describe(r):
    if r["kind"] == "fluent":
        return r["icon"] + (" (near)" if r.get("near") else "") + (" (rotated)" if r.get("rotate") else "")
    if r["kind"] == "compose":
        return f"{r['icon']} + {r['badge']} badge"
    if r["kind"] == "text":
        return f"text {r['text']!r} {r['weight']}"
    if r["kind"] == "mirror":
        return f"mirror of {r['of']}"
    return r["kind"]


def main():
    cdp, base, font = sys.argv[1:4]
    rows = [r for r in json.loads((ROOT / "data/icons/table.json").read_text())["rows"] if r["kind"] != "blank"]
    if len(sys.argv) > 4:
        only = set(json.loads((ROOT / sys.argv[4]).read_text()))
        rows = [r for r in rows if r["points"][0] in only]
    items = [{"n": i + 1, "point": r["points"][0], "label": r.get("name")} for i, r in enumerate(rows)]
    out = ROOT / ".private/v0_5" / ("review2" if len(sys.argv) > 4 else "review")
    out.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / "build/v0_5/overlay-expr.js"
    script = (ROOT / "probe/v0_5/overlay.js").read_text()
    pngs = []
    for start in range(0, len(items), PER_SHEET * BATCH):
        config = {"font": f"{base}/{font}", "rows": items[start:start + PER_SHEET * BATCH], "perSheet": PER_SHEET}
        tmp.write_text(f"const CONFIG = {json.dumps(config)};\n" + script)
        res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(tmp), "100"],
                             capture_output=True, text=True, timeout=120, check=True)
        pngs += json.loads(res.stdout)
    for i, url in enumerate(pngs):
        (out / f"r{i + 1:03}.png").write_bytes(base64.b64decode(url.split(",")[1]))
    (out / "key.txt").write_text("\n".join(
        f"{i + 1} {r['points'][0]} {r.get('name', '(no name)')}: {describe(r)}" for i, r in enumerate(rows)) + "\n")
    print(len(rows), "rows", len(pngs), "sheets")


if __name__ == "__main__":
    main()
