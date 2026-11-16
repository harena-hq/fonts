# SPDX-License-Identifier: Apache-2.0
"""Measure what Windows gives CJK under a Segoe stack; write data/v0_4/.

Only numbers come back: widths, heights, stems and ink boxes in px. The fonts that
draw these on Windows (Malgun Gothic, Yu Gothic, Microsoft YaHei and others) are
measured the way Segoe is, and their files stay on the guest; the provenance names
them by SHA-256.

1. cases.json, what is measured:
   - covered: Pretendard JP's code points in the CJK blocks that Segoe does not map.
     U+FE20-FE2D (combining half marks) are not a CJK block's and are left out.
   - symbols: those Unicode gives no script of its own (Common, Inherited). Chromium
     puts them in the run beside them, so what they measure depends on that run.
   - punctuation: the symbols that are punctuation or a space, for `halt`.
   - kana: Hiragana and Katakana letters, and their marks.
   - bases: letters to stand beside the symbols, Hangul and Han.
   - sentences, sequences: fixed text, which must add up from the rest.
2. windows/<Size>-<Weight>.json, one per Segoe face, per language, widths in px at a
   1000 px font size in DOM layout:
   - alone: each covered code point, as runs [first, last, width] over `covered`.
   - beside: {script: {"after": {cp: d}, "before": {cp: d}}}, the width of base + symbol
     and symbol + base, minus the two alone, kept where any base gives other than 0.
     A base that disagrees is listed under `base_disagrees`.
   - kern: {text: d}, every kana pair, and on Text every kana with every symbol in both
     orders, minus the two alone, nonzero only.
   - pairs, spaced: {text: d}, every ordered pair of punctuation, under the default
     text-spacing-trim and under space-all, nonzero only.
   - halt: {cp: d}, each punctuation mark under `font-feature-settings: 'halt'`, minus
     alone, nonzero only.
   - sentences, sequences: one width each, in order.
   `en` has only alone, sentences and sequences; it must equal no `lang`.
3. shapes.json: stems (the coverage 650 px above the baseline of U+3163 and U+5341),
   ink boxes for a sample, and line box heights.

Usage: python probe/v0_4/run.py <cdp-http-base> <repo-root-url> <provenance.json> <windows-fonts.txt>
"""
import json
import sys
import unicodedata
from pathlib import Path

from fontTools import unicodedata as fu
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v0"))
from run import ROOT, SEGOE, evaluate  # noqa: E402

WEIGHTS = {300: "Light", 350: "Semilight", 400: "Regular", 600: "Semibold", 700: "Bold"}
LANGS = ["", "ko", "ja", "zh-Hans", "zh-Hant"]
PJP = ROOT / "sources/pjp/public/variable/PretendardJPVariable.ttf"
V0_1 = json.loads((ROOT / "data/v0_1/segoe-ui-variable.json").read_text())
BLOCKS = [(0x2E80, 0x2FDF), (0x3000, 0x30FF), (0x3130, 0x318F), (0x3200, 0x33FF), (0x3400, 0x4DBF),
          (0x4E00, 0x9FFF), (0xAC00, 0xD7A3), (0xF900, 0xFAFF), (0xFF00, 0xFFEF), (0x20000, 0x2FFFF)]
BASES = {"hangul": "가한뷁", "han": "一設日"}
SENTENCES = ["설정 저장", "파일(F) 편집(E)", "「저장」 누르기",
             "저장하시겠습니까? 예, 아니요.",
             "Windows 11 설정", "設定を保存します。",
             "ファイル（F）、編集（E）",
             "「保存」「開く」", "コンピューターとデータベース",
             "あいうえおかきくけこさしすせそ",
             "日本語とEnglishと1234", "保存文件，然后关闭。",
             "한글とひらがなと漢字", "A設B", "A가B", "AあB",
             "ＡＢＣ１２３", "ｶﾞｷﾞｸﾞ", "ㄱㅏㄴㅣ"]
SEQUENCES = ["한글", "가", "각", "が", "か゚",
             "ガ", "カ゚", "ぱ", "パ", "ヴ", "ヷ"]
TEXTS = {"latin": "Ag", "hangul": "가", "kana": "あ", "han": "設"}
LINE_SIZES = [12, 14, 16, 20, 28, 40, 68]
SAMPLE_KO = "가나다라마바사아자차카타파하한글국의설정저장확인취소"
SAMPLE_JA = "あいうえおかさたなはまやらわんアイウエオカサタナハマヤラワン設定新機能日付時刻保存"
BATCH = 40000


def case_sets():
    segoe = set(V0_1["segoe_cmap"])
    covered = sorted(c for c in TTFont(PJP).getBestCmap()
                     if c not in segoe and any(lo <= c <= hi for lo, hi in BLOCKS))
    symbols = [c for c in covered if fu.script(chr(c)) in ("Zyyy", "Zinh")]
    punctuation = [c for c in symbols if unicodedata.category(chr(c))[0] == "P" or c == 0x3000]
    kana = [c for c in covered if fu.script(chr(c)) in ("Hira", "Kana") and 0x3041 <= c <= 0x30FF]
    return covered, symbols, punctuation, kana


def widths(cdp, page, family, weight, lang, texts, css=""):
    out = []
    for i in range(0, len(texts), BATCH):
        cases = [{"text": t, "css": css, "lang": lang} for t in texts[i:i + BATCH]]
        out += evaluate(cdp, page, "../v0_3/features.js",
                        {"family": family, "weight": weight, "cases": cases, "bases": [], "marks": [],
                         "langs": []})["cases"]
    assert len(out) == len(texts)
    return out


def runs(cps, values):
    out = []
    for c, v in zip(cps, values):
        if out and out[-1][2] == v and out[-1][1] == c - 1:
            out[-1][1] = c
        else:
            out.append([c, c, v])
    return out


def measure_lang(cdp, page, family, weight, lang, sets, text_face):
    covered, symbols, punctuation, kana = sets
    alone_w = widths(cdp, page, family, weight, lang, [chr(c) for c in covered])
    alone = dict(zip(covered, alone_w))
    doc = {"alone": runs(covered, alone_w),
           "sentences": widths(cdp, page, family, weight, lang, SENTENCES),
           "sequences": widths(cdp, page, family, weight, lang, SEQUENCES)}
    if lang == "en":
        return doc

    def deltas(pairs, css=""):
        got = widths(cdp, page, family, weight, lang, [chr(a) + chr(b) for a, b in pairs], css)
        return {chr(a) + chr(b): x - alone[a] - alone[b] for (a, b), x in zip(pairs, got)
                if abs(x - alone[a] - alone[b]) > 0.02}

    doc["beside"], doc["base_disagrees"] = {}, {}
    for script, bases in BASES.items():
        per_base = [(deltas([(ord(b), s) for s in symbols]), deltas([(s, ord(b)) for s in symbols]), b)
                    for b in bases]
        after = {str(s): per_base[0][0].get(bases[0] + chr(s)) for s in symbols
                 if bases[0] + chr(s) in per_base[0][0]}
        before = {str(s): per_base[0][1].get(chr(s) + bases[0]) for s in symbols
                  if chr(s) + bases[0] in per_base[0][1]}
        doc["beside"][script] = {"after": after, "before": before}
        odd = [chr(s) for s in symbols if any(
            abs(a.get(b + chr(s), 0) - per_base[0][0].get(bases[0] + chr(s), 0)) > 0.02
            or abs(z.get(chr(s) + b, 0) - per_base[0][1].get(chr(s) + bases[0], 0)) > 0.02
            for a, z, b in per_base)]
        doc["base_disagrees"][script] = "".join(odd)
    pairs = [(a, b) for a in kana for b in kana]
    if text_face:
        pairs += [(a, s) for a in kana for s in symbols] + [(s, a) for a in kana for s in symbols]
    doc["kern"] = deltas(pairs)
    punct_pairs = [(a, b) for a in punctuation for b in punctuation]
    doc["pairs"] = deltas(punct_pairs)
    doc["spaced"] = deltas(punct_pairs, "text-spacing-trim:space-all;")
    got = widths(cdp, page, family, weight, lang, [chr(c) for c in punctuation], "font-feature-settings:'halt';")
    doc["halt"] = {str(c): x - alone[c] for c, x in zip(punctuation, got) if abs(x - alone[c]) > 0.02}
    return doc


def shapes(cdp, page):
    faces = [[f, w] for f in ("Malgun Gothic", "Yu Gothic", "Microsoft YaHei") for w in WEIGHTS]
    stems = evaluate(cdp, page, "stems.js", {"families": faces + [["Pretendard JP Probe", w]
                                                                  for w in range(45, 931, 5)],
                                             "chars": "ㅣ十", "row": 650})
    sample = [ord(c) for c in SAMPLE_KO + SAMPLE_JA]
    ink = evaluate(cdp, page, "ink.js", {"families": faces[:10] + [["Pretendard JP Probe", 400]], "glyphs": sample})
    lines = {}
    for fam in SEGOE:
        for w in WEIGHTS:
            lines[f"{fam}|{w}"] = evaluate(cdp, page, "../v0_4/lines.js",
                                           {"family": fam, "weight": w, "texts": TEXTS, "sizes": LINE_SIZES,
                                            "langs": LANGS})
    return {"stems": stems, "ink": ink, "ink_sample": {"ko": SAMPLE_KO, "ja": SAMPLE_JA}, "lines": lines,
            "line_sizes": LINE_SIZES}


def main():
    cdp, base, prov, fonts = sys.argv[1:5]
    provenance = json.loads(Path(prov).read_text())
    assert provenance["segoe_ui_variable"] == V0_1["provenance"]["segoe_ui_variable"], \
        "a different Segoe file than v0.1's target set was read from"
    provenance["windows_fonts"] = dict(line.split() for line in Path(fonts).read_text().splitlines())
    page = f"{base}/probe/page.html"
    out = ROOT / "data/v0_4"
    (out / "windows").mkdir(parents=True, exist_ok=True)
    sets = case_sets()
    covered, symbols, punctuation, kana = sets
    (out / "cases.json").write_text(json.dumps(
        {"covered": covered, "symbols": symbols, "punctuation": punctuation, "kana": kana, "bases": BASES,
         "sentences": SENTENCES, "sequences": SEQUENCES, "langs": LANGS + ["en"]},
        indent=0, ensure_ascii=False) + "\n")
    method = "DOM span width at 1000 px under `font-family` naming only the Segoe face, `lang` on the span"
    for fam in SEGOE:
        size = fam.removeprefix("Segoe UI Variable ")
        for w, name in WEIGHTS.items():
            path = out / "windows" / f"{size}-{name}.json"
            if path.exists():
                continue
            langs = {lang: measure_lang(cdp, page, fam, w, lang, sets, size == "Text")
                     for lang in LANGS + ["en"]}
            path.write_text(json.dumps({"provenance": {**provenance, "method": method},
                                        "unit": "px at 1000 px font size", "face": {"family": fam, "weight": w},
                                        "langs": langs}, indent=0, sort_keys=True, ensure_ascii=False) + "\n")
            print(f"{size}-{name}: done", flush=True)
    doc = {"provenance": {**provenance, "method": (
               "stems: pixel coverage 650 px above the baseline; ink: pixel edges at 1000 px; lines: the "
               "height of a block with line-height: normal")},
           **shapes(cdp, page)}
    (out / "shapes.json").write_text(json.dumps(doc, indent=0, sort_keys=True, ensure_ascii=False) + "\n")
    print("shapes: done", flush=True)


if __name__ == "__main__":
    main()
