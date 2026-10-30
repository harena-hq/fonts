# SPDX-License-Identifier: Apache-2.0
"""Done-when 9: string widths of a built font against Segoe in the reference browser.

Usage: python probe/v0_1/browser.py <cdp-http-base> <repo-root-url> <font path in repo>
Exits non-zero if any string differs by more than 0.1%.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, evaluate  # noqa: E402


def main():
    cdp, base, font = sys.argv[1:4]
    strings = [s for g in json.loads((ROOT / "probe/v0/strings.json").read_text()).values() for s in g]
    widths = evaluate(cdp, f"{base}/probe/page.html", "../v0_1/browser.js",
                      {"font": f"{base}/{font}", "strings": strings, "weight": 400})
    worst = 0.0
    for s, (ours, theirs) in widths.items():
        err = (ours - theirs) / theirs
        worst = max(worst, abs(err))
        print(f"{100 * err:+.3f}%  {s}")
    print(f"worst {100 * worst:.3f}% over {len(widths)} strings ->", "PASS" if worst <= 0.001 else "FAIL")
    sys.exit(0 if worst <= 0.001 else 1)


if __name__ == "__main__":
    main()
