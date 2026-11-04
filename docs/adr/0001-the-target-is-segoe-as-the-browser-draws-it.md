# 0001 — The target is Segoe as the browser on Windows draws it

Status: **locked**, 2026-10-30. For CJK, superseded by 0005 (2026-11-04).

## Context

"Match Segoe" names more than one target:

- Segoe UI Variable is one variable font with `wght` 300–700 and `opsz` 5–36. WinUI and a CSS
  stack reach it through the named instances Small, Text and Display (`opsz` 8, 10.5 and 36).
- Segoe has no Hangul or Kana. Those come from whatever the platform falls back to, and the
  fallback differs by renderer. WinUI's native text uses Yu Gothic UI, whose kana are
  proportional and whose CJK punctuation is half width. Edge, given
  `font-family: "Segoe UI Variable Text"`, draws Japanese in **Yu Gothic**, at a full 1 em, and
  Hangul in Malgun Gothic, also at 1 em (v0, `docs/v0-feasibility.md`).

## Decision

The geometry Harena UI reproduces is what **Edge on Windows** draws for a CSS stack that names a
Segoe family:

- for Latin, the named instance at its own `opsz`. v0 measured that Edge applies it regardless
  of font size, `font-optical-sizing` and `font-variation-settings`: widths spread by at most
  0.011% over 21 conditions (`data/v0/opsz-check.json`);
- for CJK, the browser's fallback faces' advances.

Harena UI's consumers are CSS stacks, winui-svelte first. A layout sized in that browser is the
one that has to come out the same size.

## Rejected

- **Native WinUI's geometry** (Yu Gothic UI for Japanese). It is the right target for a native
  app, not for a web page. Choosing it would make Japanese labels up to 28% shorter than the
  same page on Windows. Katakana-heavy labels are hit hardest.
- **The static "Segoe UI".** It is not what WinUI 3 or its CSS reproductions name, and on the
  measured string its widths differ from Segoe UI Variable Text's by up to 1.2%
  (`opsz-check.json`).

## Consequences

- Every Segoe number is measured in Edge on Windows and carries the Windows build, the Edge
  version and the font file's version and hash.
- A native-WinUI variant would be a new decision, not a parameter.
