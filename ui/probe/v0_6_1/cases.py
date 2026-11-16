# SPDX-License-Identifier: Apache-2.0
"""Write the XAML that probe/v0_6_1/measure.ps1 loads into WinUI 3 Gallery's ScratchPad, one file
per language and label, each a row small enough to lie on screen, since UI Automation gives no
bounds for an element scrolled out of view. The ScratchPad adds the XAML namespaces itself.

Usage: python probe/v0_6_1/cases.py <out-dir>
"""
import sys
from pathlib import Path

LABELS = {"latin": "Settings", "han2": "設定", "hanka": "設定する", "kana": "カタカナ", "hangul": "설정",
          "mixed": "Save 保存", "punct": "「設定」"}
LANGS = {"none": None, "en": "en-US", "ko": "ko-KR", "ja": "ja-JP"}
SIZES = (14, 20, 28, 40)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for lk, lang in LANGS.items():
        attr = f' Language="{lang}"' if lang else ""
        for key, text in LABELS.items():
            items = [f'<TextBlock FontSize="{fs}" Text="{text}" VerticalAlignment="Top" '
                     f'AutomationProperties.AutomationId="t|{lk}|{key}|{fs}"/>' for fs in SIZES]
            items += [f'<{kind} Content="{text}" VerticalAlignment="Top" AutomationProperties.AutomationId="{k}|{lk}|{key}|14"/>'
                      for kind, k in (("Button", "b"), ("CheckBox", "c"))]
            (out / f"p{n:02d}.xaml").write_text(
                f'<StackPanel Orientation="Horizontal" Spacing="8"{attr}>' + "".join(items) + "</StackPanel>",
                encoding="utf-8")
            n += 1


if __name__ == "__main__":
    main()
