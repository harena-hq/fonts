# SPDX-License-Identifier: Apache-2.0
"""Done-when 9: a built font against Segoe UI Variable Text 400 in the reference browser.

Two layouts, both with the built font served as a web font:
- canvas measureText at 1000 px, kerning on, over probe/v0/strings.json;
- DOM span widths at 12, 14, 16, 20 and 28 px (and 1000 px), default text
  settings, over those strings and probe/v0_1/dom-strings.json (kerning-heavy
  words, spaces and NBSP, ligatures, Greek, Cyrillic, extended Latin), and the
  digits under tabular-nums.

Usage: python probe/v0_1/browser.py <cdp-http-base> <repo-root-url> <font path in repo>
Exits non-zero if any width differs by more than 0.1%.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, evaluate  # noqa: E402

TOL = 0.001
SIZES = [12, 14, 16, 20, 28, 1000]


def main():
    cdp, base, font = sys.argv[1:4]
    page = f"{base}/probe/page.html"
    # The hash in the query keeps the browser from measuring a cached older build.
    digest = hashlib.sha256((ROOT / font).read_bytes()).hexdigest()[:16]
    url = f"{base}/{font}?sha256={digest}"
    v0 = [s for g in json.loads((ROOT / "probe/v0/strings.json").read_text()).values() for s in g]
    dom = [s for g in json.loads((ROOT / "probe/v0_1/dom-strings.json").read_text()).values() for s in g]
    worst = []

    canvas = evaluate(cdp, page, "../v0_1/browser.js", {"font": url, "strings": v0, "weight": 400})
    for s, (ours, theirs) in canvas.items():
        worst.append(((ours - theirs) / theirs, f"canvas 1000 px {s!r}"))

    fams = ["Segoe UI Variable Text", "Harena UI Check"]
    for numeric, strings in (("normal", v0 + dom), ("tabular-nums", ["0123456789", "1111", "10:11"])):
        r = evaluate(cdp, page, "../v0_1/dom.js", {"font": url, "families": fams, "strings": strings,
                                                    "sizes": SIZES, "numeric": numeric})
        for px in SIZES:
            for s in strings:
                ours, theirs = r[f"Harena UI Check|{px}|{s}"], r[f"Segoe UI Variable Text|{px}|{s}"]
                worst.append(((ours - theirs) / theirs, f"DOM {px} px {numeric} {s!r}"))

    worst.sort(key=lambda w: -abs(w[0]))
    over = [w for w in worst if abs(w[0]) > TOL]
    for err, what in worst[:5]:
        print(f"{100 * err:+.3f}%  {what}")
    print(f"{len(worst)} measurements, worst {100 * abs(worst[0][0]):.3f}%, over 0.1%: {len(over)} ->",
          "PASS" if not over else "FAIL")
    sys.exit(0 if not over else 1)


if __name__ == "__main__":
    main()
