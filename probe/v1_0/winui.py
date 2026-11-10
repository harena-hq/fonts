# SPDX-License-Identifier: Apache-2.0
"""WinUI 3's widths for Harena UI J's CJK, measured again for 1.0 (PLAN.md, 1.0 item 2; ADR 0005).

The cases, the measuring app and the method are v0.7's (probe/v0_7/run.py, probe/v0_7/measure).
v0.7's data had WinUI 3 lay out text with no `Language` as under `ko-KR`; on winui-svelte's
reference guest, and on a fresh guest from the same image, it lays it out as under `ja-JP` but for a
few symbols. These files replace data/v0_7 as what J is built to:

  python probe/v1_0/winui.py collect <cases.json> <widths.json> [<cases.json> <widths.json>]...
      Measure.exe's widths for probe/v0_7/run.py's cases, given as the case files Measure.exe ran
      and the widths it wrote for each (together exactly run.py's cases); writes data/v1_0/winui.json
  python probe/v1_0/winui.py pairs-collect <dir>
      the pairs as probe/v0_7/run.py writes and names them; writes data/v1_0/pairs.json
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "probe/v0_7")]
import run  # noqa: E402  probe/v0_7/run.py

OUT = ROOT / "data/v1_0"
PROVENANCE = {
    "app": "probe/v0_7/measure, a WinUI 3 app built against Windows App SDK 2.5.4-experimental (as WinUI 3 Gallery 3.0.4.0 ships), unpackaged and self-contained",
    "measured": "2026-11-09",
    "os": "Windows 11 25H2, build 26200.8875, display language en-US, the only language",
    "method": "each case a TextBlock in the default style (XamlControlsResources), UseLayoutRounding off; its ActualWidth in px",
    "cases": "probe/v0_7/run.py",
    "reference": "winui-svelte's reference guest (the same build) gave the same widths for the labels "
                 "(data/v1_0/labels.json) and for あ, 設定する and カタカナ in each language",
}
# A smoke test of the default, not a validation of the whole: あ as the reference guest laid it out
# the same day, in px at 100 px
REFERENCE = {("none", 400, 0x3042): 81.591796875, ("ko-KR", 400, 0x3042): 100, ("ja-JP", 400, 0x3042): 81.591796875}


def width_ok(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0


def read(paths):
    widths = {}
    for p in paths:
        widths.update(json.loads(Path(p).read_text(encoding="utf-8-sig")))
    return widths


def collect(paths):
    if len(paths) % 2:
        print("give each case file with its widths", file=sys.stderr)
        return 1
    given = [c for p in paths[0::2] for c in json.loads(Path(p).read_text())]
    widths = read(paths[1::2])
    cases = run.cases()
    canon = sorted(json.dumps(c, sort_keys=True, ensure_ascii=False) for c in cases)
    if sorted(json.dumps(c, sort_keys=True, ensure_ascii=False) for c in given) != canon:
        print("the cases are not this checkout's", file=sys.stderr)
        return 1
    keys = [c["key"] for c in cases]
    if set(widths) != set(keys) or not all(width_ok(widths[k]) for k in keys):
        print(f"{len(set(keys) - set(widths))} cases unmeasured, {len(set(widths) - set(keys))} not this checkout's,"
              f" {sum(not width_ok(v) for v in widths.values())} not a width", file=sys.stderr)
        return 1
    out = {lang or "none": {str(w): {f"{c:04X}": run.width(widths, lang, w, c) for c in run.points()}
                            for w in run.WEIGHTS} for lang in run.LANGS}
    derived = [(lang, w, c) for lang, by_w in out.items() for w, by_c in by_w.items() for c, v in by_c.items()
               if not width_ok(v)]
    if derived:
        print(f"{len(derived)} widths not a width once the frame is taken off", derived[:6], file=sys.stderr)
        return 1
    unlike = [(k, out[k[0]][str(k[1])][f"{k[2]:04X}"], px) for k, px in REFERENCE.items()
              if abs(out[k[0]][str(k[1])][f"{k[2]:04X}"] - px) > 1e-6]
    if unlike:
        print("unlike the reference guest:", unlike, file=sys.stderr)
        return 1
    OUT.mkdir(exist_ok=True)
    (OUT / "winui.json").write_text(json.dumps({"provenance": PROVENANCE, "size": run.SIZE, "widths": out},
                                               indent=1, allow_nan=False) + "\n")
    print(len(cases), "widths")
    return 0


def pairs_collect(folder):
    parts = sorted(Path(folder).glob("pc*.json"))
    cases = [c for part in parts for c in json.loads(part.read_text())]
    if cases != run.pair_cases():
        print("the pair cases are not this checkout's", file=sys.stderr)
        return 1
    widths = read(part.parent / ("w" + part.name) for part in parts)
    if set(widths) != {c["key"] for c in cases} or not all(width_ok(v) for v in widths.values()):
        print("pairs unmeasured or not this checkout's", file=sys.stderr)
        return 1
    single = json.loads((OUT / "winui.json").read_text())["widths"]
    differ = {}
    for lang in run.LANGS:
        for w in run.WEIGHTS:
            parts_ = single[lang or "none"][str(w)]
            for a, b in run.pair_points():
                delta = widths[run.pair_key(lang, w, a, b)] - parts_[f"{a:04X}"] - parts_[f"{b:04X}"]
                if not math.isfinite(delta):
                    print("a pair not a width:", lang, w, f"{a:04X}+{b:04X}", file=sys.stderr)
                    return 1
                if abs(delta) > 1e-6:
                    differ.setdefault(lang or "none", {}).setdefault(str(w), {})[f"{a:04X}+{b:04X}"] = delta
    data = {"provenance": "as data/v1_0/winui.json", "size": run.SIZE, "pairs": len(run.pair_points()), "differ": differ}
    (OUT / "pairs.json").write_text(json.dumps(data, indent=1, allow_nan=False) + "\n")
    print(len(cases), "pairs;", {lang: {w: len(v) for w, v in d.items()} for lang, d in differ.items()})
    return 0


def main():
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "collect":
        return collect(args)
    if mode == "pairs-collect":
        return pairs_collect(args[0])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
