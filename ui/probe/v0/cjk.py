# SPDX-License-Identifier: Apache-2.0
"""Measure what Windows draws for CJK under a Segoe stack; write data/v0/cjk-windows.json.

Four passes on the reference browser:

1. Fallback: which platform font draws each string of cjk-strings.json under
   `font-family: "Segoe UI Variable Text"`, per `lang` (fallback.mjs).
2. Advances of the fallback faces (Malgun Gothic, Yu Gothic, Yu Gothic UI) for
   Hangul, kana, CJK punctuation, fullwidth forms and the Han in the strings.
3. Ink boxes from pixels for a sample of common characters (ink.js).
4. Stems: `ㅣ` (U+3163) and `十`, 650 px above the baseline (stems.js), for the
   Windows faces and across each CJK candidate's weight range.

Usage: python probe/v0/cjk.py <cdp-http-base> <page-base-url> <provenance.json>
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import ROOT, evaluate  # noqa: E402

STRINGS = ROOT / "probe/v0/cjk-strings.json"
WINDOWS = [["Malgun Gothic", 400], ["Malgun Gothic", 700], ["Yu Gothic", 400], ["Yu Gothic", 700],
           ["Yu Gothic UI", 400], ["Yu Gothic UI", 700]]
CANDIDATES = {"Pretendard JP Probe": (45, 930), "Noto Sans KR Probe": (100, 900),
              "Noto Sans JP Probe": (100, 900)}
SAMPLE_KO = "가나다라마바사아자차카타파하한글국의설정저장확인취소"
SAMPLE_JA = "あいうえおかさたなはまやらわんアイウエオカサタナハマヤラワン設定新機能日付時刻保存"


def main():
    cdp, base, prov = sys.argv[1:4]
    provenance = json.loads(Path(prov).read_text())
    page = f"{base}/probe/page.html"
    strings = json.loads(STRINGS.read_text())

    res = subprocess.run(["node", str(ROOT / "probe/v0/fallback.mjs"), cdp, page, str(STRINGS),
                          "Segoe UI Variable Text"], capture_output=True, text=True, timeout=600, check=True)
    fallback = json.loads(res.stdout)

    han = sorted({ord(c) for g in strings.values() for s in g for c in s if 0x4E00 <= ord(c) < 0xA000})
    glyphs = (list(range(0xAC00, 0xD7A4)) + list(range(0x3131, 0x318F)) + list(range(0x3041, 0x3097))
              + list(range(0x30A1, 0x30FD)) + list(range(0x3000, 0x3020)) + list(range(0xFF01, 0xFF5F)) + han)
    m = evaluate(cdp, page, "measure.js", {"families": WINDOWS, "glyphs": glyphs, "pairs": [], "strings": {}})
    advances = {k: {cp: row[0] for cp, row in v["glyphs"].items()} for k, v in m.items()}

    sample = [ord(c) for c in SAMPLE_KO + SAMPLE_JA]
    ink = evaluate(cdp, page, "ink.js", {"families": WINDOWS[::2], "glyphs": sample})

    fams = WINDOWS[:4] + [[f, w] for f, (lo, hi) in CANDIDATES.items() for w in range(lo, hi + 1, 5)]
    stems = evaluate(cdp, page, "stems.js", {"families": fams, "chars": "ㅣ十", "row": 650})

    doc = {"provenance": {**provenance, "method": (
               "fallback: CSS.getPlatformFontsForNode and span width at 1000 px; advances: canvas "
               "measureText at 1000 px; ink: pixel edges at 1000 px; stems: pixel coverage 650 px "
               "above the baseline")},
           "unit": "px at 1000 px font size", "fallback": fallback, "advances": advances,
           "ink": ink, "ink_sample": {"ko": SAMPLE_KO, "ja": SAMPLE_JA}, "stems": stems}
    (ROOT / "data/v0/cjk-windows.json").write_text(json.dumps(doc, indent=0, sort_keys=True,
                                                              ensure_ascii=False) + "\n")
    print("fallback", len(fallback), "strings; advances", len(advances), "faces; stems", len(stems))


if __name__ == "__main__":
    main()
