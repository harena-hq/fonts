# SPDX-License-Identifier: Apache-2.0
"""1.0 item 6: what docs/engines.md says a page can do, measured in one engine.

- keep-all: what check_engines.py counts as kind "break" in a WebKit engine, measured again with
  `word-break: keep-all`, which takes away the line-break opportunities between CJK characters. If
  the kerning lost across them is all that differs, the text is then Edge's width.
- fractions: the strings with U+2044 that check_engines.py counts as kind "coretext" in Safari,
  measured again with `font-variant-numeric: diagonal-fractions`, which asks Core Text for the
  fraction HarfBuzz makes unasked: then Edge's width.
- lines: the line box of "A", and of "A" with each J code point, at 14 px on a 20 px line and 40 px on
  a 52 px line (WinUI's Body and Display), in each face's Regular, with J after the Segoe stack: the
  given line height in every engine.

The texts are taken from the engine's file from probe/v1_0/collect.py and measured again in the
same engine, in the same page, with one more stylesheet.

Usage: python probe/v1_0/remedies.py <engine> <base-url> <engine.json> <edge.json> <out.json> [--caps JSON]
"""
import argparse
import json
import sys
import unicodedata
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "probe/v1_0"), str(ROOT / "scripts")]
from build import SIZES  # noqa: E402
from check_engines import breaks, fractions  # noqa: E402
from collect import LANGS, artifacts, digest, inputs, segoe  # noqa: E402
from drive import connect  # noqa: E402

SHEETS = {"keep-all": "div div, span { word-break: keep-all; }",
          "fractions": "div div, span { font-variant-numeric: diagonal-fractions; }"}
LINES = ((14, 20), (40, 52))


def sheet(css):
    return "data:text/css," + urllib.parse.quote(css)


def width_groups(widths, labels, inp):
    groups, keys = [], []
    for key, texts in sorted(widths.items()):
        fam, size, w, lang, how = key.split("|")
        family = f'"{fam} {size}"'
        stack = family if how == "alone" else f"{segoe(size)}, {family}"
        groups.append({"font": f"{w} 1000px {stack}", "lang": LANGS[lang], "texts": texts, "axis": "width"})
        keys.append(("widths", key, texts))
    for key, idx in sorted(labels.items()):
        lang, w = key.split("|")
        groups.append({"font": f'{w} 100px {segoe("Display")}, "Harena UI J Display"', "lang": LANGS[lang],
                       "texts": [inp["labels"][i] for i in idx], "axis": "width"})
        keys.append(("labels", key, [str(i) for i in idx]))
    return groups, keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine")
    ap.add_argument("base")
    ap.add_argument("measured")
    ap.add_argument("edge")
    ap.add_argument("out")
    ap.add_argument("--caps", default="{}")
    args = ap.parse_args()
    inp = inputs()
    r, edge = json.loads(Path(args.measured).read_text()), json.loads(Path(args.edge).read_text())
    pkg = f"{args.base}/build/npm-package"
    package = [f"{pkg}/ui.css", f"{pkg}/j.css", f"{pkg}/icons.css"]
    marks = {c for c in inp["points"] if unicodedata.category(chr(c)).startswith("M")}
    texts = ["A"] + ["A" + ("か" if c in marks else "") + chr(c) for c in inp["points"]]
    lines = [{"font": f'400 {px}px/{lh}px {segoe(size)}, "Harena UI J {size}"', "lang": LANGS[lang],
              "texts": texts, "axis": "height"}
             for size in SIZES for lang in LANGS for px, lh in LINES]
    line_keys = [f"{size}|{lang}|{px}|{lh}" for size in SIZES for lang in LANGS for px, lh in LINES]
    runs = {"keep-all": width_groups(*breaks(edge, r, inp), inp),
            "fractions": width_groups(fractions(edge, r, inp), {}, inp)}
    out = {"inputs": {"cases": digest(inp), "artifacts": artifacts(inp), "measured": digest(r["engine"])},
           "keep-all": {"widths": {}, "labels": {}}, "fractions": {"widths": {}, "labels": {}}, "lines": {}}
    engine = connect(args.engine, json.loads(args.caps))
    try:
        page = f"{args.base}/probe/page.html"
        out["engine"] = engine.identity() | {"page": engine.run(page, {"mode": "env"}, 120)}
        for name, (groups, keys) in runs.items():
            if not groups:
                continue
            values = engine.run(page, {"sheets": [sheet(SHEETS[name]), *package], "faces": [], "mode": "boxes",
                                       "groups": groups}, 3600)
            for (part, key, items), vals in zip(keys, values):
                out[name][part][key] = dict(zip(items, vals))
        values = engine.run(page, {"sheets": package, "faces": [], "mode": "boxes", "groups": lines}, 3600)
        out["lines"] = dict(zip(line_keys, values))
    finally:
        engine.close()
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print({k: sum(map(len, v["widths"].values())) + sum(map(len, v["labels"].values()))
           for k, v in out.items() if k in runs}, len(out["lines"]) * len(texts), "lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
