# SPDX-License-Identifier: Apache-2.0
"""1.0 item 5: each engine fetches, for each of v0.6's nine pages, the files Edge does (probe/v1_0/fetches.py).

Edge must fetch what v0.6 recorded, at the server and in its Resource Timing alike. An engine without
Segoe fetches the same, and on a page that names Segoe first, the package's file standing in for it:
the icons' for the icon stack, Harena UI Text Regular's for the text stack, which is fetched even for
text with no Latin, since an engine takes the line's height from the family's first available font.
Nothing else: no other file, no failed request.

Usage: python probe/v1_0/check_fetches.py <fetches-edge.json> <fetches-engine.json>...; exits non-zero on a difference.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "probe/v1_0")]
from collect import artifacts, digest, fetch_cases, inputs  # noqa: E402

STAND_IN = {'"Segoe Fluent Icons"': "HarenaUIIcons-Regular.woff2", '"Segoe UI Variable': "HarenaUI-TextRegular.woff2"}


def main():
    cases = fetch_cases()
    want_inputs = {"fetch_cases": digest(cases), "artifacts": artifacts(inputs())}
    failed = False
    for n, path in enumerate(sys.argv[1:]):
        r = json.loads(Path(path).read_text())
        if r["inputs"] != want_inputs:
            sys.exit(f"{path}: measured from other cases, probe, package or TTFs")
        wrong = []
        for name, stack, _, _, edge in cases:
            want = set(edge)
            if n:  # an engine without Segoe
                want |= {f for head, f in STAND_IN.items() if stack.startswith(head)}
            got = r["served"].get(name)
            if got != sorted(want) or r["failed"].get(name):
                wrong.append((name, got, sorted(want), r["failed"].get(name)))
            if not n and r["timing"].get(name) != sorted(want):
                wrong.append((name, "timing", r["timing"].get(name)))
        e = r["engine"]
        if e["browser"].startswith("Edg") != (not n):
            sys.exit(f"{path}: the first file must be Edge's, and only the first")
        print(f"{path}: {e['browser']}, {e['guest']}: {len(cases)} pages, {len(wrong)} unexpected", wrong)
        failed |= bool(wrong) or len(r["served"]) != len(cases)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
