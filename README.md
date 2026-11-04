# Harena UI

A UI typeface that stands in for Segoe UI Variable and Segoe Fluent Icons where they are not
installed. Its shapes come from open fonts; its geometry — advance widths, kerning, vertical
metrics and icon ink boxes — is measured from Segoe, so a layout sized under Segoe comes out the
same size under Harena UI. Named after Segoe in a font stack, it keeps the layout where Segoe is
absent; where Segoe is installed it draws only what Segoe lacks, such as Hangul, kana and Han.

| family | covers | shapes from |
|---|---|---|
| **Harena UI** Small, Text, Display | Latin, Greek, Cyrillic, Hebrew, punctuation, symbols | Open Sans |
| **Harena UI J** Small, Text, Display | Harena UI, plus Hangul, kana and Han | Open Sans, Pretendard JP |
| **Harena UI Icons** | Segoe Fluent Icons' code points | Fluent UI System Icons |

Each text family has Segoe UI Variable's three optical sizes in its name, as Windows registers
Segoe's, and its five weights: Light, Semilight, Regular, Semibold and Bold. Italic is synthesized
by the renderer, as it is for Segoe UI Variable.

## Use

Name each Harena family right after the Segoe family it stands in for:

```css
font-family: "Segoe UI Variable Text", "Segoe UI", "Harena UI J Text", sans-serif;
font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets", "Harena UI Icons";
```

A renderer takes each character from the first family that has it, so where Segoe is installed it
draws everything Segoe covers. Hangul, kana and Han, which Segoe lacks, then come from Harena UI J
instead of Windows' own fallback faces: at the widths WinUI 3 lays them out at in each language, in
Pretendard JP's shapes, and with Segoe's line height in every language, as WinUI 3 keeps it.

## Build

Python 3.12 with the pinned `requirements.txt`:

```sh
scripts/fetch_sources.sh
python scripts/build.py        # Harena UI, 15 faces
python scripts/build_j.py      # Harena UI J, 15 faces
python scripts/build_icons.py  # Harena UI Icons
python scripts/verify.py && python scripts/verify_j.py && python scripts/verify_icons.py
python scripts/build_web.py    # the web files, in dist/web
python scripts/build_css.py    # the stylesheets, in npm/
python scripts/verify_web.py && python scripts/package_npm.py   # build/npm-package
```

The built files are in `dist/`, and `SHA256SUMS`, `SHA256SUMS-J`, `SHA256SUMS-Icons` and
`SHA256SUMS-Web` pin them. The npm package is `@harena-hq/ui-font`; `npm/README.md` describes it.
`PLAN.md` is the plan and the record of what was measured; `docs/adr/` holds the decisions.

## Licence

The fonts are under the SIL Open Font License 1.1 (`OFL.txt`); the scripts are under the Apache
License 2.0 (`LICENSE`). Harena UI Icons carries outlines from Fluent UI System Icons under the MIT
License. See `THIRD_PARTY_NOTICES.md` for each source.

Segoe UI Variable and Segoe Fluent Icons are Microsoft's and are not redistributable. Only numbers
measured from them are in this repository; no outline or file of theirs is in it.
