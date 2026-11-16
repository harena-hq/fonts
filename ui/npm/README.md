# @harena-hq/ui-font

Harena UI as web fonts: a UI typeface that stands in for Segoe UI Variable and Segoe Fluent Icons
where they are not installed. Its advance widths, kerning, line metrics and icon boxes are measured
from Segoe, so a layout sized under Segoe comes out the same size.

## Entries

| import | declares |
|---|---|
| `@harena-hq/ui-font` (`index.css`) | `ui.css` and `icons.css` |
| `@harena-hq/ui-font/ui.css` | Harena UI Small, Text and Display: Latin, Greek, Cyrillic, Hebrew |
| `@harena-hq/ui-font/j.css` | Harena UI J Small, Text and Display: Harena UI plus Hangul, kana and Han |
| `@harena-hq/ui-font/icons.css` | Harena UI Icons, at Segoe Fluent Icons' code points |

Every face has five weights (Light, Semilight, Regular, Semibold, Bold), declared for the same CSS
weight ranges Segoe UI Variable answers to; italic is synthesized, as it is for Segoe. Each face is
split by `unicode-range`, so a page fetches only the files its text uses. Harena UI J reuses Harena
UI's Latin files and adds its CJK in chunks; a Korean page fetches its common Hangul in one file,
a Japanese page its common kanji in one.

## Use

```js
import '@harena-hq/ui-font/j.css';
import '@harena-hq/ui-font/icons.css';
```

Name each Harena family right after the Segoe family it stands in for:

```css
font-family: "Segoe UI Variable Text", "Segoe UI", "Harena UI J Text", sans-serif;
font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets", "Harena UI Icons";
```

A renderer takes each character from the first family that has it. Where Segoe is installed, it
draws what Segoe covers and fetches no Harena file for it; Hangul, kana and Han, which Segoe lacks,
come from Harena UI J at the widths WinUI 3 lays them out at, in each language (`lang="ja"` takes
Japanese's proportional kana and narrower punctuation). A line holding them keeps Segoe's height in
every language, as WinUI 3 draws it (a kana voicing mark written straight after a Latin
letter aside, which Edge draws from Windows).

## Licence

Fonts under the SIL Open Font License 1.1 (`OFL.txt`), with Fluent UI System Icons' outlines in
Harena UI Icons under the MIT License; stylesheets under the Apache License 2.0. See
`THIRD_PARTY_NOTICES.md`.
