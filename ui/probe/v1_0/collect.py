# SPDX-License-Identifier: Apache-2.0
"""Measure the package in one engine and write every number to one file (PLAN.md, 1.0).

The page and the package (after scripts/package_npm.py) are served from this checkout, with dist/'s
TTFs. What is measured, the same in every engine:

- widths: every v0.3 and v0.4 string in each Harena UI and Harena UI J face, with no language and
  under ko and ja, at 1000 px: in the package's family alone, in the face's whole TTF, and in the
  package's family after the Segoe stack (v0.6; the reference where Segoe is installed).
- points: every J code point outside Harena UI, alone in each J face and language at 1000 px (v0.7).
- labels: v0.7's labels, in each language and weight at 100 px, after the Segoe UI Variable Display
  stack (v0.7).
- pairs: every pair v0.7 measured, under ja in J Text at each weight at 100 px (v0.7).
- icons: Harena UI Icons' code points at 1000 px, alone and after the Segoe icon stack.
- lines: the line box of "A" under the Segoe stack alone (Windows' line where Segoe is installed),
  of "A" with J after the stack, and of "A" then each J code point with J after the stack, at 14
  and 40 px, in each J face and language (v0.6.1).
- fetches: the font files v0.6's nine pages fetch.

Results are written after every run, and a run already in the file is not repeated, so an engine
that drops its session is resumed by running the same command again: only with the same cases,
probe, package, TTFs and engine (its version and what the page sees), which the file records.

Usage: python probe/v1_0/collect.py <engine> <base-url> <out.json> --platform TEXT [--caps JSON] [--only part,...]
  engine: cdp=<http-base> or webdriver=<http-base>; base-url: this checkout's root as the engine
  reaches it.
"""
import argparse
import hashlib
import json
import math
import sys
import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "probe/v0_7"), str(ROOT / "probe/v1_0")]
from build import SIZES, WEIGHTS, face_path  # noqa: E402
from build_j import face_path_j  # noqa: E402
from build_web import chunks  # noqa: E402
from drive import connect  # noqa: E402
from run import pair_points, points  # noqa: E402
from verify_web import strings  # noqa: E402

LANGS = {"none": "", "ko": "ko", "ja": "ja"}
PARTS = ("widths", "points", "labels", "pairs", "icons", "lines", "fetches")
LINE_PX = (14, 40)
ICONS = ROOT / "dist/HarenaUIIcons-Regular.ttf"
ICON_STACK = '"Segoe Fluent Icons", "Segoe MDL2 Assets", "Harena UI Icons"'


def segoe(size):
    return f'"Segoe UI Variable {size}", "Segoe UI"'


def labels():
    from browser import LABELS  # probe/v0_7/browser.py
    return LABELS


def icon_points():
    return sorted(c for c in TTFont(ICONS, lazy=True).getBestCmap() if not chr(c).isspace())


def inputs():
    pts = points()
    return {
        "strings": strings(),
        "points": pts,
        "marks": [c for c in pts if unicodedata.category(chr(c)).startswith("M")],
        "labels": labels(),
        "pairs": [list(p) for p in pair_points()],
        "icons": icon_points(),
    }


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


def fetch_cases():
    """v0.6's nine pages: (name, font stack, lang, text, the files Edge fetches)."""
    harena_j, harena = '"Harena UI J Text"', '"Harena UI Text"'
    # 鬱 is JIS X 0208 level 2: it lives in one of the other Han parts
    rare = next(n for n, p in chunks(TTFont(face_path_j("Text", 400), lazy=True).getBestCmap(),
                                     TTFont(face_path("Text", 400), lazy=True).getBestCmap()).items() if 0x9B31 in p)
    return [
        ("Latin, Harena UI alone", harena, "", "Settings", ["HarenaUI-TextRegular.woff2"]),
        ("Latin, after Segoe", f"{segoe('Text')}, {harena_j}", "", "Settings", []),
        ("icons, after Segoe", '"Segoe Fluent Icons", "Segoe MDL2 Assets", "Harena UI Icons"', "", "\ue713\ue700", []),
        ("icons, alone", '"Harena UI Icons"', "", "\ue713\ue700", ["HarenaUIIcons-Regular.woff2"]),
        ("Hangul, after Segoe", f"{segoe('Text')}, {harena_j}", "ko", "한국어 설정", ["HarenaUIJ-TextRegular-hangul-1.woff2"]),
        ("Hangul with a rare syllable", f"{segoe('Text')}, {harena_j}", "ko", "똠방각하",
         ["HarenaUIJ-TextRegular-hangul-1.woff2", "HarenaUIJ-TextRegular-hangul-2a.woff2"]),
        ("Hangul, J alone", harena_j, "ko", "한국어 설정",
         ["HarenaUI-TextRegular.woff2", "HarenaUIJ-TextRegular-hangul-1.woff2"]),
        ("Japanese, after Segoe", f"{segoe('Text')}, {harena_j}", "ja", "設定を保存する",
         ["HarenaUIJ-TextRegular-kana.woff2", "HarenaUIJ-TextRegular-han-1.woff2"]),
        ("Japanese with a rare kanji", f"{segoe('Text')}, {harena_j}", "ja", "設定を保存する 鬱",
         ["HarenaUIJ-TextRegular-kana.woff2", "HarenaUIJ-TextRegular-han-1.woff2",
          f"HarenaUIJ-TextRegular-{rare}.woff2"]),
    ]


def runs(base, inp):
    """Every run, as (part, key, config, how to file its result). A key is filed once."""
    pkg = f"{base}/build/npm-package"
    sheets = [f"{pkg}/ui.css", f"{pkg}/j.css", f"{pkg}/icons.css"]

    def boxes(groups, faces=()):
        return {"sheets": sheets, "faces": list(faces), "mode": "boxes", "groups": groups}

    for size in SIZES:
        for w in WEIGHTS:
            for fam, ttf in (("Harena UI", face_path(size, w)), ("Harena UI J", face_path_j(size, w))):
                family, ref = f"{fam} {size}", f"Whole {fam} {size} {w}"
                hows = {"alone": f'"{family}"', "ttf": f'"{ref}"', "stack": f'{segoe(size)}, "{family}"'}
                groups, keys = [], []
                for lang, tag in LANGS.items():
                    for how, stack in hows.items():
                        groups.append({"font": f"{w} 1000px {stack}", "lang": tag, "texts": inp["strings"], "axis": "width"})
                        keys.append(f"{fam}|{size}|{w}|{lang}|{how}")
                face = {"family": ref, "url": f"{base}/{ttf.relative_to(ROOT)}", "weight": w}
                yield "widths", f"{fam}|{size}|{w}", boxes(groups, [face]), keys

    texts = [chr(c) for c in inp["points"]]
    for size in SIZES:
        for w in WEIGHTS:
            yield "points", f"{size}|{w}", boxes(
                [{"font": f'{w} 1000px "Harena UI J {size}"', "lang": tag, "texts": texts, "axis": "width"}
                 for tag in LANGS.values()]), [f"{size}|{w}|{lang}" for lang in LANGS]

    stack = f'{segoe("Display")}, "Harena UI J Display"'
    yield "labels", "all", boxes(
        [{"font": f"{w} 100px {stack}", "lang": tag, "texts": inp["labels"], "axis": "width"}
         for tag in LANGS.values() for w in WEIGHTS]), [f"{lang}|{w}" for lang in LANGS for w in WEIGHTS]

    texts = [chr(a) + chr(b) for a, b in inp["pairs"]]
    for w in WEIGHTS:
        yield "pairs", str(w), boxes(
            [{"font": f'{w} 100px "Harena UI J Text"', "lang": "ja", "texts": texts, "axis": "width"}]), [str(w)]

    texts = [chr(c) for c in inp["icons"]]
    yield "icons", "all", boxes([{"font": f"1000px {s}", "lang": "", "texts": texts, "axis": "width"}
                                 for s in ('"Harena UI Icons"', ICON_STACK)]), ["alone", "stack"]

    marks = set(inp["marks"])
    texts = ["A" + ("か" if c in marks else "") + chr(c) for c in inp["points"]]
    for size in SIZES:
        for w in WEIGHTS:
            groups, keys = [], []
            for lang, tag in LANGS.items():
                for px in LINE_PX:
                    groups.append({"font": f"{w} {px}px {segoe(size)}", "lang": tag, "texts": ["A"], "axis": "height"})
                    keys.append(f"{size}|{w}|{lang}|{px}|alone")
                    groups.append({"font": f'{w} {px}px {segoe(size)}, "Harena UI J {size}"', "lang": tag,
                                   "texts": ["A"], "axis": "height"})
                    keys.append(f"{size}|{w}|{lang}|{px}|latin")
                    groups.append({"font": f'{w} {px}px {segoe(size)}, "Harena UI J {size}"', "lang": tag,
                                   "texts": texts, "axis": "height"})
                    keys.append(f"{size}|{w}|{lang}|{px}|ours")
            yield "lines", f"{size}|{w}", boxes(groups), keys

    for name, font_stack, lang, text, _ in fetch_cases():
        yield "fetches", name, {"sheets": sheets, "mode": "fetch", "font": f"400 20px {font_stack}",
                                "lang": lang, "text": text}, None


def artifacts(inp):
    """What a measurement depends on besides the cases: the probe and its runs, the package, the TTFs."""
    files = [ROOT / f for f in ("probe/v1_0/measure.js", "probe/v1_0/collect.py", "probe/v1_0/drive.py",
                                "probe/cdp.mjs", "probe/page.html")]
    files += sorted((ROOT / "build/npm-package").glob("*.css")) + sorted((ROOT / "build/npm-package/fonts").glob("*"))
    files += sorted((ROOT / "dist").glob("*.ttf"))
    h = hashlib.sha256()
    for f in files:
        h.update(f.relative_to(ROOT).as_posix().encode() + b"\0" + hashlib.sha256(f.read_bytes()).digest())
    # and every run as configured, with this checkout's paths
    h.update(json.dumps([[part, key, config, keys] for part, key, config, keys in runs("", inp)],
                        ensure_ascii=False).encode())
    return h.hexdigest()


def expected(inp):
    """Each part's keys, and how many values each holds (a fetch: its names)."""
    out = {}
    for part, key, config, keys in runs("", inp):
        if keys is None:
            out.setdefault(part, {})[key] = None
        else:
            for k, g in zip(keys, config["groups"]):
                out.setdefault(part, {})[k] = len(g["texts"])
    return out


def well_formed(values, n):
    return (isinstance(values, list) and len(values) == n
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0
                    for v in values))


def complete(result, inp):
    """The parts and keys a run of every part files, each whole. Returns what is missing or malformed."""
    bad = []
    for part, keys in expected(inp).items():
        got = result.get(part, {})
        for key, n in keys.items():
            v = got.get(key)
            ok = (isinstance(v, list) and all(isinstance(x, str) for x in v)) if n is None else well_formed(v, n)
            if not ok:
                bad.append(f"{part}|{key}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine")
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--caps", default="{}")
    ap.add_argument("--platform", required=True,
                    help="the guest as no engine reports it: OS build and the font and text libraries' versions")
    ap.add_argument("--only", default=",".join(PARTS))
    args = ap.parse_args()
    only = set(args.only.split(","))
    assert only <= set(PARTS), f"--only takes {PARTS}"

    inp = inputs()
    out_path = Path(args.out)
    result = json.loads(out_path.read_text()) if out_path.exists() else {}
    want = {k: digest(v) for k, v in inp.items()} | {"artifacts": artifacts(inp)}
    if result.setdefault("inputs", want) != want:
        sys.exit(f"{out_path} was measured from other cases, probe, package or TTFs; move it aside")
    result.setdefault("done", [])

    engine = connect(args.engine, json.loads(args.caps))
    try:
        page = f"{args.base}/probe/page.html"
        identity = engine.identity() | {"page": engine.run(page, {"mode": "env"}, 120), "guest": args.platform}
        if result.setdefault("engine", identity) != identity:
            sys.exit(f"{out_path} was measured in another engine: {result['engine']}; this is {identity}")
        lengths = expected(inp)
        # a run marked done stays done only while everything it filed is whole
        missing = set(complete(result, inp))
        broken = {f"{part}|{key}" for part, key, _, keys in runs("", inp)
                  if any(f"{part}|{k}" in missing for k in (keys or [key]))}
        result["done"] = [d for d in result["done"] if d not in broken]
        for part, key, config, keys in runs(args.base, inp):
            if part not in only or f"{part}|{key}" in result["done"]:
                continue
            value = engine.run(page, config, 3600)
            filed = result.setdefault(part, {})
            if keys is None:
                assert isinstance(value, list) and all(isinstance(v, str) for v in value), (part, key, value)
                filed[key] = sorted(value)
            else:
                assert len(value) == len(keys), (part, key, len(value))
                for k, v in zip(keys, value):
                    assert well_formed(v, lengths[part][k]), (part, k)
                filed.update(zip(keys, value))
            result["done"].append(f"{part}|{key}")
            tmp = out_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(result, ensure_ascii=False))
            tmp.replace(out_path)
            print(part, key, flush=True)
    finally:
        engine.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
