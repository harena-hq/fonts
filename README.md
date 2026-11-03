# Harena UI

A UI typeface that stands in for Segoe UI Variable and Segoe Fluent Icons where they are not
installed. Its shapes come from open fonts; its geometry — advance widths, kerning, vertical
metrics and icon ink boxes — is measured from Segoe, so a layout sized under Segoe comes out the
same size under Harena UI. Named after Segoe in a font stack, it changes nothing on Windows and
keeps the layout everywhere else.

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
draws everything Segoe covers, and Harena UI is not used.

## Build

Python 3.12 with the pinned `requirements.txt`:

```sh
scripts/fetch_sources.sh
python scripts/build.py        # Harena UI, 15 faces
python scripts/build_j.py      # Harena UI J, 15 faces
python scripts/build_icons.py  # Harena UI Icons
python scripts/verify.py && python scripts/verify_j.py && python scripts/verify_icons.py
```

The built files are in `dist/`, and `SHA256SUMS`, `SHA256SUMS-J` and `SHA256SUMS-Icons` pin them.
`PLAN.md` is the plan and the record of what was measured; `docs/adr/` holds the decisions.

## Licence

The fonts are under the SIL Open Font License 1.1 (`OFL.txt`); the scripts are under the Apache
License 2.0 (`LICENSE`). Harena UI Icons carries outlines from Fluent UI System Icons under the MIT
License. See `THIRD_PARTY_NOTICES.md` for each source.

Segoe UI Variable and Segoe Fluent Icons are Microsoft's and are not redistributable. Only numbers
measured from them are in this repository; no outline or file of theirs is in it.
