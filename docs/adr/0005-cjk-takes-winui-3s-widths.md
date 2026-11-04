# 0005 — CJK takes WinUI 3's widths

Status: **locked**, 2026-11-04. Amends 0001 for CJK; 0001 stands for Latin.

## Context

ADR 0001 took, for CJK, the advances of the faces Edge falls back to under a Segoe stack, and
rejected native WinUI's: a page on Windows would otherwise lay its Japanese out differently from
the same page where the font is missing.

Two later versions removed that reason:

- Since v0.6 the package names Harena UI J after Segoe, so on Windows too a page's CJK is drawn
  from Harena UI J, not from Edge's fallback. Edge's own fallback widths are no longer anything a
  page shows.
- Since v0.6.1 J's lines are WinUI 3's height in every language, because winui-svelte reproduces
  WinUI 3 (PLAN.md, v0.6.1).

WinUI 3 lays CJK out unlike Edge. Under `ja-JP` it uses Yu Gothic UI's proportional kana and half-
or two-thirds-width punctuation, with that face's kerning. Under `ko-KR`, and with no `Language`,
it uses Malgun Gothic's widths. Semibold, which Malgun Gothic lacks, comes 2% wider.

## Decision

Harena UI J's CJK advances are the widths WinUI 3 lays each code point and pair out at, in each
language and weight. They are measured exactly by a WinUI 3 app (`probe/v0_7/measure`) and
recorded in `data/v0_7`:

- **Default advance:** WinUI 3's width with no `Language`. `ko-KR` lays out the same in every case.
- **Japanese:** under the `JAN` language system, a `dist` single adjustment gives `ja-JP`'s widths.
  `dist` is used because a page cannot turn it off as it can `kern`.
- **Pairs:** the pairs WinUI 3 lays out apart from their parts are recorded under `kern`, per
  language.
- **Removed:** v0.4's `halt` and its per-script Edge run widths, so Edge has nothing to trim by.
  The `KOR`, `ZHS` and `ZHT` systems are also removed: the first equals the default, and Chinese
  is out of scope.

## Rejected

- **Keeping Edge's widths.** These are widths that only Edge's own fallback produced, and the
  package now replaces that fallback on Windows too. Under `ja`, they make a winui-svelte label
  up to a third longer than the WinUI 3 control it reproduces (`カタカナ` 160 px against 120 px
  at 40 px).
- **Measuring through the Gallery's UI Automation.** It gives whole pixels only, and only for
  elements on screen. That is enough to identify faces but not to build from, and at minutes per
  few hundred characters it is too slow.

## Consequences

- J is drawn as WinUI 3 draws CJK: a winui-svelte layout in Japanese or Korean keeps the size of
  the WinUI 3 control it reproduces, in Edge, on Linux and on macOS.
- A page that sets `font-kerning: none` loses the Japanese pair kerning, as it would in WinUI 3
  by turning kerning off; the widths themselves stay.
- A kana and a combining sound mark that Unicode composes are drawn as the composed letter:
  HarfBuzz composes them, and no font can stop it. WinUI 3 lays some of these out apart, wider
  or narrower: 5 pairs with no language and 3 under `ja-JP`, a few px at 100 px. Text is
  normally precomposed.
- Chinese text takes the default widths.
