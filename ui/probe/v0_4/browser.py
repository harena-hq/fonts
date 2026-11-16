# SPDX-License-Identifier: Apache-2.0
"""v0.4 item 4: every Harena UI J face against the Segoe face it stands for, in the reference
browser, under each language: what Windows' CJK fallback gives beside what the J face gives, live.

Per face at its Segoe weight, in DOM layout:
- at 1000 px: every covered code point, every symbol before and after Hangul and Han, every kana
  pair (and on Text, kana with every symbol), every punctuation pair under the default
  text-spacing-trim and under space-all, and after Hangul, Han, Hiragana and Katakana, the sentences
  and the sequences;
- at 12, 14, 16, 20 and 28 px: the same but for the kana pairs that do not kern and punctuation
  pairs with a letter first, and with every 20th Hangul and Han; on Text at 14 px, all kana pairs.

Left out, as PLAN.md's Locked note lists, and counted: U+3099 and U+309A outside kana sequences,
U+FF5F and U+FF60 alone and in a symbol pair, U+FA2E and U+FA2F before Han, a symbol before a letter
where Windows' run takes the symbol's font (the width after the letter differs from before it), and
punctuation pairs in which Windows' first font draws the second (a change other than 0 or half an
em), and U+30FB beside punctuation outside Japanese. U+309A under Chinese is left out where it
is not zero alone, in Semibold and Bold. Text with a character Pretendard JP lacks is left out too.
So are, again as PLAN.md's: U+FF5F and U+FF60 beside one of ten symbols after Hangul with no language,
which the symbol's font draws at 1 em, and U+30FB after a bracket around other letters after kana,
which Windows trims and the rest there it does not. In Semibold and Bold at 20 px and below, a
character Windows emboldens itself takes a whole pixel: there the width may be over by that for up to
each such character in the text, and what is is counted apart.

The page hashes the bytes it loaded, which must be the built face's. Line boxes at `line-height:
normal` are reported apart, not judged: PLAN.md leaves Japanese lines to v0.6. Tolerances are
v0.2's: 0.1% of Windows' width, or for a Small face within one layout unit.

Usage: python probe/v0_4/browser.py <cdp-http-base> <repo-root-url> [Size-Weight ...] [--px 1000 ...]
Exits non-zero if any width is outside that.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from fontTools import unicodedata as fu
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, evaluate  # noqa: E402

WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
EXPECTED = [(s, w) for s in ("Small", "Text", "Display") for w in WEIGHTS]
LANGS = ["", "en", "ko", "ja", "zh-Hans", "zh-Hant"]
SMALL = [12, 14, 16, 20, 28]
MARKS = "゙゚"
ODD = "｟｠"
BATCH = 30000
SPACE_ALL = "text-spacing-trim:space-all;"
DOT = "\u30FB"
EVERY_SIZE = "\uAC00\uAC01\uD55C\uBDC1\u4E00\u8A2D\u65E5"
CONTEXT = "\uAC00\u8A2D\u3042\u30A2"
ODD_BESIDE = "〖〗〘〙〚〛〜〝〞〟"
BRACKETS = {"（": "）", "「": "」", "『": "』", "【": "】", "〔": "〕", "〈": "〉", "《": "》", "［": "］", "｛": "｝"}
WHOLE_PIXEL = (12, 14, 16, 20)


def emboldened(alone):
    """What Windows emboldens itself: 19.53 units over a whole or half em, at 1000 px."""
    return {chr(c) for c, v in alone.items() if abs(v % 500 - 19.53125) < 0.02}


def expand(runs):
    return {c: v for first, last, v in runs for c in range(first, last + 1)}


def workload(size, w, cases, data, cmap):
    """{px: [case]}, and what was left out, per reason."""
    left = {}

    def out(reason):
        left[reason] = left.get(reason, 0) + 1

    symbols = [chr(c) for c in cases["symbols"]]
    punct = [chr(c) for c in cases["punctuation"]]
    kana = [chr(c) for c in cases["kana"]]
    full, small, kana_pairs = [], [], []
    for lang in LANGS:
        d = data[lang]
        for i, c in enumerate(cases["covered"]):
            ch = chr(c)
            if ch in MARKS:
                out("marks alone")
                continue
            if ch in ODD:
                out("U+FF5F, U+FF60 alone")
                continue
            case = {"text": ch, "css": "", "lang": lang}
            full.append(case)
            if fu.script(ch) not in ("Hang", "Hani") or i % 20 == 0 or ch in EVERY_SIZE:
                small.append(case)
        fixed = [t for t in cases["sentences"] if all(ord(x) in cmap for x in t)]
        out_sentences = len(cases["sentences"]) - len(fixed)
        if out_sentences:
            left["text Pretendard JP lacks"] = left.get("text Pretendard JP lacks", 0) + out_sentences
        whole_em_mark = lang.startswith("zh") and expand(d["alone"])[0x309A] > 0
        seq = [t for t in cases["sequences"] if not (whole_em_mark and "\u309A" in t)]
        if len(seq) != len(cases["sequences"]):
            left["marks alone"] = left.get("marks alone", 0) + len(cases["sequences"]) - len(seq)
        for t in fixed + seq:
            case = {"text": t, "css": "", "lang": lang}
            full.append(case)
            small.append(case)
        if lang == "en":
            continue
        for name, bases in cases["bases"].items():
            beside = d["beside"][name]
            for s in symbols:
                if s in MARKS:
                    out("marks after a letter of no kana")
                    continue
                texts = [bases[0] + s]
                if beside["after"].get(str(ord(s)), 0) == beside["before"].get(str(ord(s)), 0):
                    texts.append(s + bases[0])
                else:
                    out("a symbol's font draws the letter after it")
                for t in texts:
                    case = {"text": t, "css": "", "lang": lang}
                    full.append(case)
                    small.append(case)
        # A symbol's most usual change after kana is its width in the run; wider than that, the
        # pair is a kana whose font draws the symbol too (PLAN.md)
        mode_after = {s: Counter(round(d["kern"].get(a + s, 0), 3) for a in kana).most_common(1)[0][0]
                      for s in symbols if s not in MARKS} if size == "Text" else {}
        kana_set = set(kana)
        for text in d["kern"]:
            # what kerns, at every size
            if any(x in MARKS for x in text):
                continue
            pair = [x for x in text if x not in kana_set]
            if len(pair) == 1 and pair[0] in mode_after and d["kern"][text] > mode_after[pair[0]] + 0.02:
                out("a kana's font draws the symbol beside it")
                continue
            small.append({"text": text, "css": "", "lang": lang})
        for a in kana:
            if a in MARKS:
                continue
            for b in kana:
                if b not in MARKS:
                    kana_pairs.append({"text": a + b, "css": "", "lang": lang})
            if size == "Text":
                for s in symbols:
                    if s in MARKS:
                        continue
                    for text in (a + s, s + a):
                        if d["kern"].get(text, 0) > mode_after.get(s, 0) + 0.02:
                            out("a kana's font draws the symbol beside it")
                        else:
                            full.append({"text": text, "css": "", "lang": lang})
        # A kana run that starts at a closing bracket, after other letters inside the bracket
        for o, c in BRACKETS.items():
            for p in punct:
                if p == DOT and lang == "":
                    out("U+30FB after a bracket around other letters after kana")
                    continue
                full.append({"text": f"\u30A2{o}F{c}{p}", "css": "", "lang": lang})
        for group, css in (("pairs", ""), ("spaced", SPACE_ALL)):
            for a in punct:
                for b in punct:
                    if DOT in a + b and lang != "ja":
                        out("U+30FB beside punctuation outside Japanese")
                        continue
                    if not css:
                        # The pair in a run, after a letter, where the run's font is the letter's
                        for letter in CONTEXT:
                            if (lang == "" and letter == CONTEXT[0] and (a in ODD or b in ODD)
                                    and (a in ODD_BESIDE or b in ODD_BESIDE)):
                                out("U+FF5F, U+FF60 beside a symbol whose font draws them")
                                continue
                            full.append({"text": letter + a + b, "css": "", "lang": lang})
                    if a in ODD or b in ODD:
                        out("U+FF5F, U+FF60 in a pair")
                        continue
                    if abs(d[group].get(a + b, 0)) > 0.02 and abs(d[group].get(a + b, 0) + 500) > 0.02:
                        out("a symbol's font draws the symbol after it")
                        continue
                    case = {"text": a + b, "css": css, "lang": lang}
                    full.append(case)
                    small.append(case)
    work = {1000: full + kana_pairs}
    bold = {lang: emboldened(expand(data[lang]["alone"])) for lang in LANGS}
    for px in SMALL:
        work[px] = small + (kana_pairs if size == "Text" and px == 14 else [])
        if px in WHOLE_PIXEL:
            work[px] = [{**c, "bold": sum(x in bold[c["lang"]] for x in c["text"])} for c in work[px]]
    return work, left


def main():
    args = sys.argv[1:]
    cdp, base = args[:2]
    rest = args[2:]
    sizes = [int(x) for x in rest[rest.index("--px") + 1:]] if "--px" in rest else [1000, *SMALL]
    rest = rest[:rest.index("--px")] if "--px" in rest else rest
    page = f"{base}/probe/page.html"
    cases = json.loads((ROOT / "data/v0_4/cases.json").read_text())
    if not cases["covered"] or not cases["kana"] or not cases["punctuation"]:
        raise SystemExit("data/v0_4/cases.json is empty or incomplete")
    total, unit, over, left_total, lines = 0, 0, [], {}, []
    rounded = 0
    for size, w in EXPECTED:
        name = f"{size}-{WEIGHTS[w]}"
        if rest and name not in rest:
            continue
        path = ROOT / "dist" / f"HarenaUIJ-{size}{WEIGHTS[w]}.ttf"
        cmap = TTFont(path).getBestCmap()
        data = json.loads((ROOT / f"data/v0_4/windows/{name}.json").read_text())["langs"]
        work, left = workload(size, w, cases, data, cmap)
        for k, v in left.items():
            left_total[k] = left_total.get(k, 0) + v
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        url = f"{base}/{path.relative_to(ROOT)}?sha256={digest[:16]}"
        family = f"Segoe UI Variable {size}"
        count, u, bad = 0, 0, []
        for px in sizes:
            for i in range(0, len(work[px]), BATCH):
                batch = work[px][i:i + BATCH]
                r = evaluate(cdp, page, "../v0_4/browser.js", {
                    "font": url, "family": family, "weight": w, "small": size == "Small", "px": px,
                    "cases": batch})
                if r["sha256"] != digest:
                    raise SystemExit(f"{name}: the page loaded other bytes than the built face")
                if r["count"] != len(batch):
                    raise SystemExit(f"{name}: {r['count']} widths compared, not every case")
                count, u = count + r["count"], u + r["unit"]
                rounded += r["rounded"]
                bad += r["over"]
        total, unit = total + count, unit + u
        over += [(name, *row) for row in bad]
        print(f"{name}: {count} measurements, {u} within one layout unit, {len(bad)} outside", flush=True)
        for row in sorted(bad, key=lambda o: -abs(o[1] - o[2]) / max(o[2], 1e-9))[:6]:
            print(f"  {row[0]}: {row[1]:.3f} vs {row[2]:.3f}", flush=True)
        ours = evaluate(cdp, page, "../v0_4/lines.js", {
            "font": url, "family": "Harena Probe", "weight": w, "langs": ["", "ko", "ja"],
            "texts": {"latin": "Ag", "hangul": "가", "kana": "あ", "han": "設"},
            "sizes": [12, 14, 16, 20, 28, 40, 68]})
        theirs = json.loads((ROOT / "data/v0_4/shapes.json").read_text())["lines"][f"{family}|{w}"]
        for lang, rows in ours.items():
            for text, row in rows.items():
                for s, h in row.items():
                    if h != theirs[lang][text][s]:
                        lines.append((name, lang, text, int(s), h, theirs[lang][text][s]))
    short = {}
    for _, lang, text, s, h, t in lines:
        key = (lang, text, s, h - t)
        short[key] = short.get(key, 0) + 1
    print("line boxes differing from Windows (reported, not judged):")
    for (lang, text, s, d), n in sorted(short.items()):
        print(f"  lang={lang!r} {text} {s} px: {d:+g} px on {n} faces")
    print("left out as PLAN.md's:", ", ".join(f"{k} {v}" for k, v in sorted(left_total.items())))
    print(f"over by the whole pixel of a character Windows emboldens, at 20 px and below: {rounded}")
    print(f"{total} measurements; over 0.1% but within one layout unit: {unit}; outside both: "
          f"{len(over)} ->", "PASS" if not over else "FAIL")
    sys.exit(0 if not over else 1)


if __name__ == "__main__":
    main()
