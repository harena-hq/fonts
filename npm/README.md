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
UI's Latin files and adds its CJK in chunks.

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
come from Harena UI J at the widths Windows gives them. Each chunk takes the line height of the face
Windows draws most of it with when no language is set. Under `lang="ko"` or `"ja"`, and for the few
characters Windows draws from yet another face, a line holding them can be up to a few pixels taller
or shorter than on Windows.

## Licence

Fonts under the SIL Open Font License 1.1 (`OFL.txt`), with Fluent UI System Icons' outlines in
Harena UI Icons under the MIT License; stylesheets under the Apache License 2.0. See
`THIRD_PARTY_NOTICES.md`.
