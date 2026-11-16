# SPDX-License-Identifier: Apache-2.0
"""Choose each row's Fluent icon among its stem's drawings: filled if the Segoe name says so or its
ink is nearer the Segoe glyph's, at the first size of 16, 20, 24. Writes `icon` into
data/icons/table.json. Ink, not shape: a cosine favours a filled drawing of an outlined glyph.

Usage: python probe/v0_5/style.py <cdp-http-base> <repo-root-url>
"""
import json
import re
import subprocess
import sys

from stages import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from build_icons import MAX_LOSS, compose  # noqa: E402

SIZES = ["16", "20", "24"]
FILLED = re.compile(r"Solid|Fill|Bold")


def main():
    cdp, base = sys.argv[1:3]
    path = ROOT / "data/icons/table.json"
    doc = json.loads(path.read_text())
    fluent = json.loads((ROOT / "build/v0_5/fluent.json").read_text())
    def drawing(stem, style):
        return next((f"{stem}_{z}_{style}" for z in SIZES if f"{stem}_{z}_{style}" in fluent), None)
    for row in doc["rows"]:
        if row["kind"] == "compose" and "icon" not in row:
            on_grid = f"{row['base']}_20_regular"  # the recipe's grid
            row["icon"] = on_grid if on_grid in fluent else drawing(row["base"], "regular")
            if compose(row["icon"], row["badge"])[1] >= MAX_LOSS:  # the recipe would eat the base: the base alone
                row.update(kind="fluent", stem=row.pop("base"), near=True)
                row.pop("badge")
                row.pop("icon")
    todo = []
    for row in doc["rows"]:
        if row["kind"] == "fluent" and "icon" not in row:
            icons = [i for i in (drawing(row["stem"], "regular"), drawing(row["stem"], "filled")) if i]
            todo.append({"point": row["points"][0], "icons": icons})
    tmp = ROOT / "build/v0_5/style-expr.js"
    script = (ROOT / "probe/v0_5/style.js").read_text()
    scores = {}
    for start in range(0, len(todo), 200):
        config = {"family": "Segoe Fluent Icons", "url": "/build/v0_5/fluent.json", "rows": todo[start:start + 200]}
        tmp.write_text(f"const CONFIG = {json.dumps(config)};\n" + script)
        res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, f"{base}/probe/page.html", str(tmp), "120"],
                             capture_output=True, text=True, timeout=140, check=True)
        scores.update(json.loads(res.stdout))
    count = {"regular": 0, "filled": 0}
    for row in doc["rows"]:
        if row["kind"] == "fluent" and "icon" not in row:
            s = scores[row["points"][0]]
            regular, filled = drawing(row["stem"], "regular"), drawing(row["stem"], "filled")
            nearer = regular and filled and abs(s[filled] - s["segoe"]) < abs(s[regular] - s["segoe"])
            take_filled = filled and (not regular or FILLED.search(row.get("name", "")) or nearer)
            if row.get("style") == "regular" and regular:
                take_filled = False
            if row.get("style") == "filled" and filled:
                take_filled = True
            row["icon"] = filled if take_filled else regular
            count["filled" if take_filled else "regular"] += 1
    path.write_text(json.dumps(doc, indent=0, ensure_ascii=False, sort_keys=True).replace(",\n", ", ").replace("{\n", "{").replace("\n}", "}") + "\n")
    print(count)


if __name__ == "__main__":
    main()
