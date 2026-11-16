# SPDX-License-Identifier: Apache-2.0
"""Rank Fluent's icons against each Segoe glyph, inside the guest; write build/v0_5/rank.json.

Usage: python probe/v0_5/rank.py <cdp-http-base> <repo-root-url>
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    cdp, base = sys.argv[1:3]
    rows = json.loads((ROOT / "data/v0_5/segoe-icons.json").read_text())["points"]
    names = json.loads((ROOT / "data/v0_5/segoe-names.json").read_text())["names"]
    point_of = {}
    for point, group, _, _ in rows:
        point_of.setdefault(group, point)
    by_name = {}
    for point, name in names.items():
        by_name.setdefault(name, point)
    known = {r[0] for r in rows}
    pairs = [[p, by_name[n.replace("Mirrored", "")]] for p, n in names.items() if p in known
             and "Mirrored" in n and n.replace("Mirrored", "") in by_name and by_name[n.replace("Mirrored", "")] in known]
    config = {"family": "Segoe Fluent Icons", "url": "/build/v0_5/fluent.json", "points": list(point_of.values()), "pairs": pairs}
    expr = f"const CONFIG = {json.dumps(config)};\n" + (ROOT / "probe/v0_5/rank.js").read_text()
    tmp = ROOT / "build/v0_5/rank-expr.js"
    tmp.write_text(expr)
    res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(tmp), "580"],
                         capture_output=True, text=True, timeout=600, check=True)
    (ROOT / "build/v0_5/rank.json").write_text(res.stdout)
    data = json.loads(res.stdout)
    print(len(data["nearest"]), "ranked;", len(data["pairs"]), "mirror pairs")


if __name__ == "__main__":
    main()
