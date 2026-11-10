# SPDX-License-Identifier: Apache-2.0
"""1.0 items 3 and 4: an engine's file from probe/v1_0/collect.py, against Edge's on Windows.

Edge with Segoe installed is the reference (PLAN.md, 1.0). An engine without Segoe lays the package
out wherever Edge lays Segoe out, so what it gives after the Segoe stack is compared with what Edge
gives there. Each difference is either a fault, which fails the check, or one of the counted kinds
below, each with its cause, which is reported by count (PLAN.md, 1.0 item 6; docs/engines.md):

3. widths
   a. each string after the Segoe stack, in every Harena UI and J face and language, against Edge's
      after the stack, within v0.3's tolerance: 0.1%, or a layout unit of each engine's;
   b. the same string in the package's family alone, against Edge's alone, within the same;
   c. each J code point alone, against data/v1_0 (WinUI 3) for its language and weight, within half
      a font unit and a layout unit (v0.7);
   d. the labels after the Segoe stack, within 1 px of WinUI 3's (data/v1_0/labels.json, v0.7);
   e. the pairs under ja, against their parts and kern within one and a half font units and a layout
      unit; a Hangul syllable and a sound mark counted apart (v0.7);
   f. Harena UI Icons' code points, alone and after the icon stack, against Edge's after the stack,
      within a layout unit.
4. line boxes: "A", and "A" with each J code point, with J after the Segoe stack, against the line of
   "A" Edge lays out in Segoe at the engine's device pixel ratio, at 14 and 40 px in every face and
   language. A line is the font's ascent and descent, each rounded by the engine's own rule (ROUNDING);
   an engine must give exactly what its rule gives, and Edge what Blink's gives; where the rules
   differ, the engine's line is counted.

Usage: python probe/v1_0/check_engines.py <edge.json> <edge-2x.json> <engine.json>:<remedies.json>...
  remedies.json: probe/v1_0/remedies.py's file for the engine (the measurements docs/engines.md and the
  kinds "break" and "coretext" rest on).
  edge.json and edge-2x.json: Edge at device pixel ratio 1 and 2 (`--caps '{"deviceScaleFactor": 2}'`
  does not round as a display at 200% does: Edge 2x is started with --force-device-scale-factor=2).
Exits non-zero on a fault.
"""
import collections
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "probe/v0_7"), str(ROOT / "probe/v1_0"), str(ROOT / "scripts")]
from browser import composed, hangul_mark, label_cases  # noqa: E402
from build import face_path  # noqa: E402
from build_j import face_path_j  # noqa: E402
from fontTools.pens.boundsPen import BoundsPen  # noqa: E402
from collect import artifacts, digest, expected, inputs, well_formed  # noqa: E402

UPM = 2048
WINUI_LANG = {"none": "none", "ko": "ko-KR", "ja": "ja-JP"}
PARTS = ("widths", "points", "labels", "pairs", "icons", "lines")
# Default_Ignorable_Code_Point (Unicode 16, DerivedCoreProperties.txt)
IGNORABLE = [(0xAD, 0xAD), (0x34F, 0x34F), (0x61C, 0x61C), (0x115F, 0x1160), (0x17B4, 0x17B5), (0x180B, 0x180F),
             (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F),
             (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A),
             (0xE0000, 0xE0FFF)]
SOUND_MARKS = {0x3099, 0x309A}
# a fraction alone, which diagonal-fractions can be asked for on just itself (docs/engines.md)
FRACTION = re.compile("[0-9]+\u2044[0-9]+")

# Each engine's rounding of a line's ascent and descent: to what step, in device pixels or CSS px, and
# whether to the nearest or up. Recorded from the engines (PLAN.md, 1.0 item 4).
ROUNDING = {"blink": ("device", "nearest"), "webkit": ("css", "nearest"), "gecko": ("device", "up")}

# The counted kinds: name -> (engines, cause). An engine's difference of a kind it is not listed for
# is a fault.
COUNTED = {
    "fallback": ({"blink", "webkit", "gecko"},
                 "a character no face of the family maps: drawn by the system's fonts, which differ by system;"
                 " unbounded, since no font of ours sets the width"),
    "ignorable": ({"blink", "webkit", "gecko"},
                  "an unmapped default ignorable, left to the engine: Blink and Gecko keep the run whole and give"
                  " Edge's package; WebKit splits it there and draws what follows from the system's fonts,"
                  " unbounded as fallback is; alone, nothing wide"),
    "break": ({"webkit"},
              "WebKit measures text in pieces at each line-break opportunity (between CJK characters, before"
              " U+00B4), so a kern pair across one is lost: the same text with word-break: keep-all, measured"
              " again in the engine (probe/v1_0/remedies.py), is Edge's, and the width lies between Edge's and"
              " its glyphs' advances"),
    "coretext": ({"safari"},
                 "Core Text: no automatic fraction at U+2044 (with diagonal-fractions, measured again, Edge's);"
                 " a combining mark that composes with nothing before it is as wide as its ink left of the origin"
                 " where it comes first or alone, and wider by no more than that after a character"),
    "rounding": ({"webkit", "gecko"}, "the engine rounds a line's ascent and descent by another rule (ROUNDING)"),
    "segoe": ({"blink", "webkit", "gecko"},
              "the package is off Segoe here in Edge itself (Edge's package alone against its Segoe stack), as v0.3"
              " left it: bare combining marks, and a letter before CGJ; the engine gives Edge's package"),
}


def ignorable(c):
    return any(lo <= c <= hi for lo, hi in IGNORABLE)


def cjk(c):
    return unicodedata.east_asian_width(chr(c)) in "WF"


def engine_kind(engine):
    b = engine["browser"].lower()
    if b.startswith(("chrome", "edg")):
        return "blink"
    if b.startswith("firefox"):
        return "gecko"
    if b.startswith(("safari", "minibrowser")):
        return "webkit"
    raise ValueError(f"unknown engine {engine['browser']}")


def kinds_of(engine):
    """The engine's names in COUNTED: its kind, and "safari" for Core Text."""
    k = engine_kind(engine)
    return {k} | ({"safari"} if engine["browser"].lower().startswith("safari") else set())


def unit(engine):
    """The engine's layout unit in px: Gecko's app unit is 1/60 px, Blink's and WebKit's 1/64."""
    return 1 / 60 if engine_kind(engine) == "gecko" else 1 / 64


def coverage():
    ui = set(TTFont(ROOT / "dist/HarenaUI-TextRegular.ttf", lazy=True).getBestCmap())
    return {"Harena UI": ui, "Harena UI J": ui | set(TTFont(ROOT / "dist/HarenaUIJ-TextRegular.ttf", lazy=True).getBestCmap())}


def string_kind(s, mapped, engine):
    """The counted kind a string's difference may be, for this engine, or None."""
    unmapped = {ord(c) for c in s} - mapped
    if any(not ignorable(c) for c in unmapped):
        return "fallback"
    if unmapped:
        return "ignorable"
    names = kinds_of(engine)
    # a sound mark left in the text once composed is one that composes with nothing before it
    lone = SOUND_MARKS & {ord(c) for c in unicodedata.normalize("NFC", s)}
    if "safari" in names and ("⁄" in s or lone or unicodedata.category(s[0]).startswith("M")):
        return "coretext"
    if "webkit" in names and any(cjk(ord(c)) or c == "´" for c in s):
        return "break"
    return None


_faces = {}


def face(fam, size, w):
    path = face_path(size, int(w)) if fam == "Harena UI" else face_path_j(size, int(w))
    if path not in _faces:
        f = TTFont(path)
        _faces[path] = (f.getBestCmap(), f["hmtx"], f.getGlyphSet())
    return _faces[path]


def ink_left(cmap, glyphs, c):
    """How far a glyph's ink reaches left of its origin, in units (0 if it does not)."""
    pen = BoundsPen(glyphs)
    glyphs[cmap[c]].draw(pen)
    return max(0, -pen.bounds[0]) if pen.bounds else 0


def lone_mark(fam, size, w, c, px):
    """Core Text's width for a mark that composes with nothing before it: its ink left of the origin."""
    cmap, _, glyphs = face(fam, size, w)
    return ink_left(cmap, glyphs, c) * px / UPM


def nominal(s, fam, size, w, px):
    """The sum of the string's glyphs' advances, a lone mark at its ink left of the origin: what shaping
    with no fraction, ligature or kerning gives."""
    total = 0
    for c in map(ord, s):
        for f in dict.fromkeys((fam, "Harena UI")):  # J's Latin is Harena UI's
            cmap, hmtx, glyphs = face(f, size, w)
            if c in cmap:
                total += max(hmtx[cmap[c]][0], ink_left(cmap, glyphs, c))
                break
    return total * px / UPM


def line(size, w, px, dpr, rule):
    """A line's height by a rounding rule, from the face's ascent and descent."""
    hhea = TTFont(face_path(size, int(w)), lazy=True)["hhea"]
    where, how = ROUNDING[rule]
    step = 1 / dpr if where == "device" else 1
    r = (lambda x: math.ceil(x / step - 1e-9) * step) if how == "up" else (lambda x: math.floor(x / step + 0.5) * step)
    return r(hhea.ascent * px / UPM) + r(-hhea.descent * px / UPM)


def whole(r, inp):
    """Each measured part's keys, each whole; what is missing or malformed."""
    want = expected(inp)
    return [f"{p}|{k}" for p in PARTS for k, n in want[p].items() if not well_formed(r.get(p, {}).get(k), n)]


def fractions(edge, r, inp):
    """The strings with U+2044 ({key: [string]}) Safari's file differs from Edge's in: what
    probe/v1_0/remedies.py measures again with diagonal-fractions."""
    e, lu, cover, widths = r["engine"], unit(r["engine"]), coverage(), {}
    if "safari" not in kinds_of(e):
        return widths
    for key, ours in r["widths"].items():
        if key.endswith(("|stack", "|alone")):
            for s, a, b in zip(inp["strings"], ours, edge["widths"][key]):
                if abs(a - b) > max(b / 1000, lu) and FRACTION.fullmatch(s) and string_kind(s, cover[key.split("|")[0]], e) == "coretext":
                    widths.setdefault(key, []).append(s)
    return widths


def breaks(edge, r, inp):
    """The strings ({key: [string]}) and labels ({key: [index]}) a WebKit engine's file differs from
    Edge's in as kind "break" may: what probe/v1_0/remedies.py measures again with keep-all."""
    e, lu, cover, widths, labels = r["engine"], unit(r["engine"]), coverage(), {}, {}
    if "webkit" not in kinds_of(e):
        return widths, labels
    for key, ours in r["widths"].items():
        if key.endswith(("|stack", "|alone")):
            for s, a, b in zip(inp["strings"], ours, edge["widths"][key]):
                if abs(a - b) > max(b / 1000, lu) and string_kind(s, cover[key.split("|")[0]], e) == "break":
                    widths.setdefault(key, []).append(s)
    winui = json.loads((ROOT / "data/v1_0/labels.json").read_text())["widths"]
    for key, values in r["labels"].items():
        lang, w = key.split("|")
        for i, px in enumerate(values):
            if abs(px - winui[f"{WINUI_LANG[lang]}|{w}|{i}"]) > 1 and any(cjk(ord(c)) for c in inp["labels"][i]):
                labels.setdefault(key, []).append(i)
    return widths, labels


class Tally:
    def __init__(self, engine):
        self.names, self.faults, self.counted = kinds_of(engine), [], collections.Counter()

    def differ(self, kind, item):
        if kind and COUNTED[kind][0] & self.names:
            self.counted[kind] += 1
        else:
            self.faults.append(item)

    def report(self, label, measured, extra=""):
        print(f"   {label}: {measured} measured, {len(self.faults)} faults; counted {dict(self.counted)}{extra}",
              self.faults[:4])
        return bool(self.faults)


def check(edge, edges, r, inp, data, labels, differs, cover, remedies):
    keep = (remedies or {}).get("keep-all")
    frac = (remedies or {}).get("fractions", {}).get("widths", {})
    e = r["engine"]
    lu = unit(e)
    failed = False
    within = lambda a, b: abs(a - b) <= max(b / 1000, lu)  # noqa: E731

    for label, how in (("3a. widths after Segoe", "stack"), ("3b. widths alone", "alone")):
        t, measured = Tally(e), 0
        for key, ours in r["widths"].items():
            if not key.endswith("|" + how):
                continue
            mapped = cover[key.split("|")[0]]
            stack = edge["widths"][key.rsplit("|", 1)[0] + "|stack"]
            alone = edge["widths"][key.rsplit("|", 1)[0] + "|alone"]
            fam, size, w = key.split("|")[:3]
            for s, a, b, x, y in zip(inp["strings"], ours, edge["widths"][key], stack, alone):
                measured += 1
                if within(a, b):
                    continue
                kind = string_kind(s, mapped, e)
                nom = nominal(s, fam, size, w, 1000)
                top = nom * 1.001 + lu
                if kind == "break":  # shown: with no line-break opportunity in it, it is Edge's; and the
                    # kerning lost moves it from Edge's toward its glyphs' advances, and no further
                    again = (keep or {}).get("widths", {}).get(key, {}).get(s)
                    slack = max(nom / 1000, lu)
                    lo, hi = min(b, nom) - slack, max(b, nom) + slack
                    kind = kind if again is not None and within(again, b) and lo <= a <= hi else None
                elif kind == "ignorable" and "webkit" not in kinds_of(e):
                    # Blink and Gecko keep the run whole: Edge's package
                    kind = kind if within(a, y) else None
                elif kind == "coretext" and FRACTION.fullmatch(s):
                    # unfractioned: with diagonal-fractions, measured again in the engine, it is Edge's
                    again = frac.get(key, {}).get(s)
                    kind = kind if again is not None and within(again, b) and b < a <= top else None
                elif kind == "coretext" and "\u2044" in s:
                    # a fraction among other figures, which diagonal-fractions would turn too: wider than
                    # Edge's, within its glyphs' advances (bounded, not shown)
                    kind = kind if b < a <= top else None
                elif kind == "coretext":
                    # a mark that composes with nothing before it: wider, by no more than the marks' ink
                    # left of their origins (bounded, not predicted: Core Text places such a mark by
                    # rules this probe does not model)
                    ink = sum(lone_mark(f, size, w, ord(c), 1000) for c in s if unicodedata.category(c).startswith("M")
                              for f in [fam if ord(c) in face(fam, size, w)[0] else "Harena UI"])
                    kind = kind if b < a <= b + ink + lu else None
                elif kind is None and how == "stack" and not within(y, x):
                    # off Segoe in Edge itself: the engine must give Edge's package
                    kind = "segoe" if within(a, y) else None
                t.differ(kind, (key, s[:24], a, b))
        failed |= t.report(label, measured)

    t, measured = Tally(e), 0
    for key, widths in r["points"].items():
        size, w, lang = key.split("|")
        for c, px in zip(inp["points"], widths):
            want = 10 * data[WINUI_LANG[lang]][w][f"{c:04X}"]
            measured += 1
            if abs(px - want) > 1000 / UPM / 2 + lu:
                lone = c in SOUND_MARKS and abs(px - lone_mark("Harena UI J", size, w, c, 1000)) <= lu
                # an engine that treats a default ignorable as one draws it at nothing
                t.differ("ignorable" if ignorable(c) and px <= lu else "coretext" if lone else None,
                         (key, f"U+{c:04X}", px, want))
    failed |= t.report("3c. code points", measured)

    t, measured, worst = Tally(e), 0, 0
    for key, widths in r["labels"].items():
        lang, w = key.split("|")
        for i, px in enumerate(widths):
            ref = labels[f"{WINUI_LANG[lang]}|{w}|{i}"]
            measured += 1
            if abs(px - ref) > 1:
                worst = max(worst, abs(px - ref) / ref)
                text = inp["labels"][i]
                again = (keep or {}).get("labels", {}).get(key, {}).get(str(i))
                nom = nominal(text, "Harena UI J", "Display", w, 100)
                lo, hi = min(ref, nom) - 1, max(ref, nom) + 1  # v0.7's 1 px against WinUI 3
                shown = (any(cjk(ord(c)) for c in text) and again is not None and abs(again - ref) <= 1
                         and lo <= px <= hi)
                t.differ("break" if shown else None, (key, text, px, ref))
    failed |= t.report("3d. labels", measured, f" (most {worst:.2%} apart)")

    t, measured = Tally(e), 0
    for w, widths in r["pairs"].items():
        parts, kern = data["ja-JP"][w], differs.get("ja-JP", {}).get(w, {})
        for (a, b), px in zip(inp["pairs"], widths):
            c = composed(a, b)
            k = kern.get(f"{a:04X}+{b:04X}", 0)
            want = parts[f"{c:04X}"] if c else parts[f"{a:04X}"] + parts[f"{b:04X}"] + k
            measured += 1
            if abs(px - want) <= 100 / UPM * 1.5 + lu or hangul_mark(a, b):
                continue  # v0.7 counts a Hangul syllable and a sound mark in Edge too
            unkerned = not c and abs(px - (want - k)) <= 100 / UPM * 1.5 + lu
            # a sound mark that composes with nothing before it: first, it is wider by exactly its ink
            # left of the origin; after a character, by no more than that (bounded, not predicted)
            if a in SOUND_MARKS and b in SOUND_MARKS:  # two: bounded by both marks' ink
                lone = want < px <= want + sum(lone_mark("Harena UI J", "Text", w, m, 100) for m in (a, b)) + lu
            elif a in SOUND_MARKS:
                lone = not c and abs(px - (want + lone_mark("Harena UI J", "Text", w, a, 100))) <= 100 / UPM * 1.5 + lu
            else:
                lone = not c and b in SOUND_MARKS and want < px <= want + lone_mark("Harena UI J", "Text", w, b, 100) + lu
            t.differ("coretext" if lone else "break" if unkerned else None,
                     (w, f"U+{a:04X}+U+{b:04X}", px, want))
    failed |= t.report("3e. pairs under ja", measured)

    t = Tally(e)
    for key in ("alone", "stack"):
        for c, a, b in zip(inp["icons"], r["icons"][key], edge["icons"]["stack"]):
            if abs(a - b) > lu:
                t.differ(None, (key, f"U+{c:04X}", a, b))
    failed |= t.report("3f. icons", 2 * len(inp["icons"]))

    dpr = e["page"]["devicePixelRatio"]
    ref = edges.get(dpr)
    if ref is None:
        print(f"   4. line boxes: no Edge reference at device pixel ratio {dpr}")
        return True
    t, measured, heights, rule = Tally(e), 0, {}, engine_kind(e)
    for key, ours in r["lines"].items():
        if key.endswith("|alone"):
            continue
        base = key.rsplit("|", 1)[0]
        size, w, _, px = base.split("|")
        [segoe] = ref["lines"][base + "|alone"]
        theirs, blink = line(size, w, int(px), dpr, rule), line(size, w, int(px), dpr, "blink")
        if abs(segoe - blink) > 1e-6:
            t.faults.append((base, "Edge is not Blink's rule", segoe, blink))
        for h in ours:
            measured += 1
            heights.setdefault(f"{px} px", collections.Counter())[f"{h:g} (Segoe {segoe:g})"] += 1
            if abs(h - theirs) > 1e-6:  # every line is the engine's rule's
                t.faults.append((key, h, "not the engine's rule", theirs))
            elif abs(h - segoe) > 1e-6:
                t.differ("rounding", (key, h, segoe, theirs))
    failed |= t.report(f"4. line boxes at device pixel ratio {dpr}, rounding {ROUNDING[rule]}", measured,
                       f"; heights {dict((k, dict(v)) for k, v in heights.items())}")

    # docs/engines.md: a line-height given in px is that height in every engine
    t, measured = Tally(e), 0
    for key, values in (remedies or {}).get("lines", {}).items():
        lh = int(key.split("|")[3])
        for h in values:
            measured += 1
            if h != lh:
                t.faults.append((key, h, lh))
    if not measured:
        t.faults.append("no remedies file: line-height in px not measured")
    failed |= t.report("4'. line boxes on a line-height in px", measured)
    return failed


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    inp = inputs()
    inputs_digest = {k: digest(v) for k, v in inp.items()} | {"artifacts": artifacts(inp)}
    data = json.loads((ROOT / "data/v1_0/winui.json").read_text())["widths"]
    ref = json.loads((ROOT / "data/v1_0/labels.json").read_text())
    if ref["provenance"]["cases_sha256"] != digest(label_cases()):
        sys.exit("data/v1_0/labels.json was measured from other label cases")
    differs = json.loads((ROOT / "data/v1_0/pairs.json").read_text())["differ"]
    files = {}
    args = [a.split(":", 1) for a in sys.argv[3:]]
    keeps = {path: json.loads(Path(k).read_text()) for path, *k in args for k in k}
    for path in [*sys.argv[1:3], *(a[0] for a in args)]:
        r = json.loads(Path(path).read_text())
        if r["inputs"] != inputs_digest:
            sys.exit(f"{path}: measured from other cases, probe, package or TTFs")
        missing = whole(r, inp)
        if missing:
            sys.exit(f"{path}: incomplete, {len(missing)} keys missing or malformed, {missing[:4]}")
        files[path] = r
    edge, edge2 = files[sys.argv[1]], files[sys.argv[2]]
    for r, dpr in ((edge, 1), (edge2, 2)):
        if engine_kind(r["engine"]) != "blink" or r["engine"]["page"]["devicePixelRatio"] != dpr:
            sys.exit(f"the reference at {dpr}x is not Edge at device pixel ratio {dpr}")
    failed = False
    # what is measured in layout units hardly depends on the display's scale: within two layout units
    for part in ("widths", "points", "labels", "pairs", "icons"):
        n = sum(abs(a - b) > 2 / 64 + 1e-9 for k in edge[part] for a, b in zip(edge[part][k], edge2[part][k]))
        if n:
            print(f"Edge's {part} at device pixel ratio 2: {n} beyond two layout units of 1's")
            failed = True
    cover = coverage()
    for path, *_ in args:
        r = files[path]
        e = r["engine"]
        keep = keeps.get(path)
        if keep and (keep["inputs"] != {"cases": digest(inp), "artifacts": inputs_digest["artifacts"],
                                        "measured": digest(e)}
                     or keep["engine"] != {k: e[k] for k in keep["engine"]}):
            sys.exit(f"{path}: its remedies file was measured for another file, probe, package or engine")
        print(f"{path}: {e['browser']} ({e['protocol']}), {e['guest']}; device pixel ratio {e['page']['devicePixelRatio']}")
        failed |= check(edge, {1: edge, 2: edge2}, r, inp, data, ref["widths"], differs, cover, keep)
    print("counted kinds:", *(f"\n  {k} ({', '.join(sorted(v[0]))}): {v[1]}" for k, v in COUNTED.items()))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
