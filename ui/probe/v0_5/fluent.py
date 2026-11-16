# SPDX-License-Identifier: Apache-2.0
"""Collect Fluent's SVG paths into build/v0_5/fluent.json, for the page that ranks and draws them.
A path may open with a relative moveto, so each starts from the origin, not where the last one ended.

Usage: python probe/v0_5/fluent.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "sources/fluent/package/icons"
NAME = re.compile(r"(.+)_(16|20|24)_(regular|filled)\.svg")


def main():
    out, other = {}, 0
    for f in sorted(ICONS.iterdir()):
        m = NAME.fullmatch(f.name)
        if not m:
            continue
        text = f.read_text()
        paths = re.findall(r'<path[^>]*\sd="([^"]+)"', text)
        if not paths or re.search(r"<(circle|rect|ellipse|polygon|line|g|defs|mask|clipPath)\b|transform=", text):
            other += 1
            continue
        out[f.stem] = {"s": m[1], "z": int(m[2]), "k": m[3][0], "d": " M0 0 ".join(paths), "e": "evenodd" in text}
    (ROOT / "build/v0_5").mkdir(parents=True, exist_ok=True)
    (ROOT / "build/v0_5/fluent.json").write_text(json.dumps(out))
    print(len(out), "icons", len({v["s"] for v in out.values()}), "names;", other, "drawn otherwise")


if __name__ == "__main__":
    main()
