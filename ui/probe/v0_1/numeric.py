# SPDX-License-Identifier: Apache-2.0
"""Measure Segoe UI Variable Text 400's digits under `font-variant-numeric:
tabular-nums` in the reference browser; write data/v0_1/segoe-tnum.json.

Segoe's default `1` is narrower than its other digits; under tabular-nums all ten
share one advance. Measured in DOM layout at 1000 px.

Usage: python probe/v0_1/numeric.py <cdp-http-base> <repo-root-url> <provenance.json>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, evaluate  # noqa: E402


def main():
    cdp, base, prov = sys.argv[1:4]
    provenance = json.loads(Path(prov).read_text())
    digits = [str(i) for i in range(10)]
    r = evaluate(cdp, f"{base}/probe/page.html", "../v0_1/dom.js",
                 {"families": ["Segoe UI Variable Text"], "strings": digits, "sizes": [1000],
                  "numeric": "tabular-nums"})
    doc = {"provenance": {**provenance, "method": "DOM span width at 1000 px, font-variant-numeric: tabular-nums"},
           "unit": "px at 1000 px font size",
           "tabular": {str(ord(d)): r[f"Segoe UI Variable Text|1000|{d}"] for d in digits}}
    (ROOT / "data/v0_1/segoe-tnum.json").write_text(json.dumps(doc, indent=0, sort_keys=True) + "\n")
    print(doc["tabular"])


if __name__ == "__main__":
    main()
