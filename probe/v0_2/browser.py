# SPDX-License-Identifier: Apache-2.0
"""v0.2 item 4: every built face against the Segoe face it stands for, in the
reference browser.

v0.1's Done-when 9, per face at its Segoe weight: canvas measureText at 1000 px
over probe/v0/strings.json, and DOM span widths at 12, 14, 16, 20, 28 and
1000 px over those strings and probe/v0_1/dom-strings.json, plus digits under
tabular-nums; the DOM measurements are made upright and in italic, which the
browser synthesizes for both fonts. Each face is served as a web font declared
at exactly its weight, so this checks each face's geometry; which face a CSS
weight reaches is delivery's (v0.6).

A DOM width is laid out in whole layout units (1/64 px). Segoe's Small faces
kern by fractions of a font unit, which a font cannot store (PLAN.md v0.2, item
4), so a short string at a small size may land one layout unit away; a Small
face's DOM measurement passes within 0.1% or within one layout unit, and the
count that needed the unit is printed. Canvas widths, which are not quantized,
and the Text and Display faces, which Segoe kerns in whole units, get no
allowance.

Usage: python probe/v0_2/browser.py <cdp-http-base> <repo-root-url>
Exits non-zero if any width is outside that.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, evaluate  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from build import FACES, face_name, face_path  # noqa: E402

TOL = 0.001
LAYOUT_UNIT = 1 / 64  # px
SIZES = [12, 14, 16, 20, 28, 1000]


def main():
    cdp, base = sys.argv[1:3]
    page = f"{base}/probe/page.html"
    v0 = [s for g in json.loads((ROOT / "probe/v0/strings.json").read_text()).values() for s in g]
    dom = [s for g in json.loads((ROOT / "probe/v0_1/dom-strings.json").read_text()).values() for s in g]
    worst, per_face = [], {}
    for size, w in FACES:
        path = face_path(size, w)
        # The hash in the query keeps the browser from measuring a cached older build.
        url = f"{base}/{path.relative_to(ROOT)}?sha256={hashlib.sha256(path.read_bytes()).hexdigest()[:16]}"
        rows = evaluate(cdp, page, "../v0_2/browser.js", {
            "font": url, "family": f"Segoe UI Variable {size}", "weight": w, "canvas": v0,
            "dom": {"normal": v0 + dom, "tabular-nums": ["0123456789", "1111", "10:11", "7777"]},
            "sizes": SIZES})
        errs = [((ours - theirs) / theirs, f"{face_name(size, w)} {what}",
                 # within one layout unit, in px at the measured size
                 size == "Small" and what.startswith("DOM") and abs(ours - theirs) * int(what.split()[1]) / 1000
                 <= LAYOUT_UNIT + 1e-9)
                for what, ours, theirs in rows]
        per_face[face_name(size, w)] = max(abs(e[0]) for e in errs)
        worst += errs
        print(f"{face_name(size, w)}: {len(errs)} measurements, worst {100 * per_face[face_name(size, w)]:.3f}%",
              flush=True)
    worst.sort(key=lambda e: -abs(e[0]))
    over = [e for e in worst if abs(e[0]) > TOL and not e[2]]
    unit = [e for e in worst if abs(e[0]) > TOL and e[2]]
    for err, what, _ in worst[:5]:
        print(f"{100 * err:+.3f}%  {what}")
    print(f"{len(worst)} measurements, worst {100 * abs(worst[0][0]):.3f}%; over 0.1% but within one "
          f"layout unit: {len(unit)}; outside both: {len(over)} ->", "PASS" if not over else "FAIL")
    sys.exit(0 if not over else 1)


if __name__ == "__main__":
    main()
