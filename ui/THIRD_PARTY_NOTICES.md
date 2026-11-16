# Third-party notices — Harena UI

Harena UI, Harena UI J and Harena UI Icons are derivative works. They are **not** distributed by,
endorsed by or verified against any upstream project, and no upstream checksum can validate the
shipped files: they are new files.

Every input is pinned, and the pins are executable: `scripts/fetch_sources.sh` downloads each one
and refuses to continue unless its SHA-256 matches. To reproduce:

```sh
scripts/fetch_sources.sh
python scripts/build.py && python scripts/build_j.py && python scripts/build_icons.py
```

No upstream Reserved Font Name is used. Pretendard JP reserves "Pretendard JP"; Open Sans reserves
none. Only outlines are taken, never a name.

Segoe UI Variable and Segoe Fluent Icons are **not** sources. They were measured, and only numbers
from them (advances, kerning, vertical metrics, ink boxes, code points and Microsoft's published
names) are in this repository. No outline or file of theirs is in it or in the fonts.

## Sources

### Open Sans

- Upstream: `google/fonts` at commit `6157dfaa640ca5738b4d1a7070fe389c3036d7fc`, `ofl/opensans/OpenSans[wdth,wght].ttf`
- Licence: OFL-1.1 (text: `docs/LICENSE-Open-Sans.txt`)
- Used for: every Latin, Greek, Cyrillic and Hebrew outline in all three families, instanced at each face's
  weight, with spacing, kerning and vertical metrics replaced by Segoe UI Variable's measured values.

### Pretendard JP 1.3.9

- Upstream: https://github.com/orioncactus/pretendard/releases/download/v1.3.9/PretendardJP-1.3.9.zip
- SHA-256: `8dab678c371a1530106ca643b76b2b80d47653d5ba670b01265b48e4c6615d63`
- Licence: OFL-1.1, with Reserved Font Name "Pretendard JP" (text: `docs/LICENSE-Pretendard-JP.txt`)
- Used for: Hangul, kana, Han and CJK punctuation in Harena UI J, instanced from the variable font,
  scaled and spaced to the widths Windows gives them; and the symbols Harena UI Icons draws as text
  that Harena UI J lacks. Pretendard's own name table credits Inter, Noto Sans CJK (Source Han Sans)
  and M PLUS 1p as its sources.

### Fluent UI System Icons

- Upstream: https://registry.npmjs.org/@fluentui/svg-icons/-/svg-icons-1.1.345.tgz
- SHA-256: `6610366b1eb5ce4ce70c95d11accbf8858b01ec81c71d31bc6493586ac8cc905`
- Licence: MIT (text: `docs/LICENSE-Fluent-UI-System-Icons.txt`)
- Used for: the outlines of Harena UI Icons, scaled to Segoe Fluent Icons' measured ink boxes, some
  mirrored, rotated or combined with a badge, as `data/icons/table.json` records per row.

## Inputs that are not in the fonts

These are pinned and fetched, but no outline of theirs ships.

- **SymbolIconManager**'s Segoe Fluent mapping, at commit `8bf48d1ce7f1dd5ff2e1ed48410a62e6cabeacce`
  (MIT): candidate Fluent names for Segoe code points, which were then reviewed one by one.
- **Noto Sans**, **Noto Sans CJK** and **Selawik** (OFL-1.1): measured as alternatives while choosing
  the sources (`docs/v0-feasibility.md`, ADRs 0002 and 0003).
