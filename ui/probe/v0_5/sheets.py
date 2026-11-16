# SPDX-License-Identifier: Apache-2.0
"""Draw rows on sheets under .private/v0_5/<run>/, with a key file naming each row's candidates.

Usage: python probe/v0_5/sheets.py <cdp-http-base> <repo-root-url> <run> <seed> <rows.json|pick> [candidates.json]
`pick` takes every row build/v0_5/stages.json leaves to a pick. A rows file is a list of group ids.
"""
import base64
import json
import random
import subprocess
import sys

from stages import ROOT

PER_SHEET = 10
BATCH = 5  # sheets per page: all 103 on one page timed out in headless Edge, five do not
FILLED = ("Solid", "Fill", "Bold")


def main():
    cdp, base, run, seed, which = sys.argv[1:6]
    source = sys.argv[6] if len(sys.argv) > 6 else "build/v0_5/candidates.json"
    stages = json.loads((ROOT / "build/v0_5/stages.json").read_text())
    candidates = json.loads((ROOT / source).read_text())
    if which == "pick":
        groups = [g for g, s in stages.items() if s["stage"] == "pick"]
    else:
        groups = json.loads((ROOT / which).read_text())
    rng = random.Random(int(seed))
    rows = []
    for i, g in enumerate(groups):
        cand = list(candidates[g])
        rng.shuffle(cand)
        s = stages[g]
        rows.append({"n": i + 1, "group": g, "point": s["point"], "label": s["name"], "cand": cand,
                     "filled": any(w in (s["name"] or "") for w in FILLED)})
    config = {"family": "Segoe Fluent Icons", "url": "/build/v0_5/fluent.json", "rows": rows, "perSheet": PER_SHEET}
    pngs = []
    tmp = ROOT / "build/v0_5/sheet-expr.js"
    script = (ROOT / "probe/v0_5/sheet.js").read_text()
    for start in range(0, len(rows), PER_SHEET * BATCH):
        part = {**config, "rows": rows[start:start + PER_SHEET * BATCH]}
        tmp.write_text(f"const CONFIG = {json.dumps(part)};\n" + script)
        res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(tmp), "100"],
                             capture_output=True, text=True, timeout=120, check=True)
        pngs += json.loads(res.stdout)
    out = ROOT / ".private/v0_5" / run
    out.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(pngs):
        (out / f"s{i + 1:03}.png").write_bytes(base64.b64decode(url.split(",")[1]))
    (out / "rows.json").write_text(json.dumps(rows))
    (out / "key.txt").write_text("\n".join(
        f"{r['n']} {r['label'] or '(no name)'}: " + " ".join(f"{'ABCDEFGH'[j]}={s}" for j, s in enumerate(r["cand"]))
        for r in rows) + "\n")
    print(len(rows), "rows", len(pngs), "sheets in", out)


if __name__ == "__main__":
    main()
