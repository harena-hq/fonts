# 0005 — CJK takes WinUI 3's widths

Status: **locked**, 2026-11-04; amended 2026-11-09 (no language). Amends 0001 for CJK; 0001 stands
for Latin.

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
or two-thirds-width punctuation, with that face's kerning, and with no `Language` the same but for
a few symbols. Under `ko-KR` it uses Malgun Gothic's widths. Semibold, which Malgun Gothic lacks,
comes 2% wider.

## Decision

Harena UI J's CJK advances are the widths WinUI 3 lays each code point and pair out at, in each
language and weight. They are measured exactly by a WinUI 3 app (`probe/v0_7/measure`) and
recorded in `data/v0_7`, and since J 0.8.0 (the amendment below) in `data/v1_0`:

- **Default advance:** WinUI 3's width with no `Language`.
- **Japanese and Korean:** under the `JAN` and `KOR` language systems, a `dist` single adjustment
  gives `ja-JP`'s and `ko-KR`'s widths where they differ from the default. `dist` is used because a
  page cannot turn it off as it can `kern`.
- **Pairs:** the pairs WinUI 3 lays out apart from their parts are recorded under `kern`, per
  language.
- **Removed:** v0.4's `halt` and its per-script Edge run widths, so Edge has nothing to trim by.
  The `ZHS` and `ZHT` systems are also removed: Chinese is out of scope.

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
  or narrower: 5 pairs under `ko-KR` and 3 with no language and under `ja-JP`, a few px at 100
  px (2026-11-09; v0.7's guest had 5 with no language). Text is
  normally precomposed.
- Chinese text takes the default widths.

## Amendment, 2026-11-09 — no language is Japanese's

v0.7 measured WinUI 3 with no `Language` laying CJK out as under `ko-KR`, and J's default advances
were those, with no `KOR` system. Re-measured for 1.0 with the same app and cases, WinUI 3 with no
`Language` lays it out as under `ja-JP` instead: kana, punctuation and pairs at Yu Gothic UI's
widths, but for 10 squared unit symbols in every weight (`㎏` 70 px at 100 px, 72 in Semibold and
Bold, against 100 in either language, 102 in Korean Semibold) and one Han, `𠮟` (U+20B9F), in Semibold and Bold, which takes `ko-KR`'s width.
It does so on winui-svelte's reference guest, which has run since September, and on a fresh guest
from the same image; both are build 26200.8875 with `en-US` the only language. The guest v0.7
measured on is gone, and what made it differ is not known. `ja-JP` reproduces v0.7's widths
exactly, and `ko-KR` but for `𠮟` in Semibold and Bold (102 px, against 100).

So the reference guest's behaviour is the target: J's default advances are the new no-language
widths (`data/v1_0`), and `KOR` returns, with `ko-KR`'s widths under `dist` as `JAN` has
`ja-JP`'s. A page with no `lang` now lays Japanese out as WinUI 3 does, and so does Edge on
Windows: this changes Windows, deliberately (PLAN.md, 1.0 item 2).

*Rejected:* keeping v0.7's default. It matches a guest that no longer exists and differs from the
reference guest by up to a third of a label's width (`カタカナ` 400 px against 298 at 100 px).
