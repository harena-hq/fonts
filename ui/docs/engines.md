# Harena UI off Windows: what each engine does, and what a page can do about it

The package is matched to Segoe as Edge draws it on Windows. Off Windows there is no Segoe, so the
package draws everything, and each engine lays it out by its own rules. 1.0 measured the package in
WebKit on macOS (Safari, standing for WKWebView), WebKitGTK, and Chrome and Firefox on macOS and
Linux, against Edge on Windows (PLAN.md, 1.0; `probe/v1_0/check_engines.py`).

What follows is what does not come out as on Windows, and why. None of it can be fixed in the fonts
or their `@font-face` rules without changing Windows too; each item says what a page using the
package (winui-svelte, the Harena app) can do instead.

## What is the same everywhere

- Every width of the Latin, Greek, Cyrillic and CJK that the fonts draw, alone and in strings, in
  every face and language, except as listed below; Chrome on both systems lays out every one as Edge
  lays out the package.
  Where Edge's package is itself off Segoe (a run of bare combining marks, 0.65% narrower; a
  letter before U+034F COMBINING GRAPHEME JOINER), every engine gives Edge's package, not Segoe
  (Safari aside for the bare marks: below).
- Every Harena UI Icons width.
- The files a page fetches: the ones Edge fetches, and where a page names Segoe first, the package's
  own file standing in for it (Edge draws that part from Segoe). Off Windows the Latin file is
  fetched even for text with no Latin: an engine takes the line's height from the family's first
  font.
- The line box in Chrome, at 1x and 2x (the scales measured), and in WebKit at 1x.

## The line box: give `line-height` in px

At `line-height: normal`, a line is the font's ascent and descent, each rounded to a pixel by the
engine's own rule:

| Engine | Rounds each of ascent and descent | 14 px text at 1x / 2x | 40 px text at 1x / 2x |
| --- | --- | --- | --- |
| Edge, Chrome (Blink) | to the nearest device pixel | 19 / 18.5 | 53 / 53 |
| Safari, WebKitGTK (WebKit) | to the nearest CSS pixel | 19 / 19 | 53 / 53 |
| Firefox (Gecko) | up, to a device pixel | 20 / 19.5 | 55 / 54 |

Edge on Windows at 200% gives 18.5 as Chrome does: what Windows shows depends on the scale too. The
heights are of Segoe's metrics, which the package copies; changing them to suit one rule moves
Windows.

**What a page can do:** give `line-height` as a length, as WinUI does (its type ramp gives every
style a line height in px: Body is 14 px on 20 px). A line is then that height in every engine:
measured for 14 px on 20 px and 40 px on 52 px, with every J code point, in all six
(`probe/v1_0/remedies.py`).

## Kerning across a line-break opportunity is lost in WebKit

WebKit measures text in pieces split at each line-break opportunity, and a kerning pair that spans one
is not applied. Between two CJK characters there is an opportunity almost everywhere, so in Safari,
WKWebView and WebKitGTK the kerning WinUI 3 applies between kana, and between a CJK character and
punctuation, is lost: Japanese labels come out up to 2.1% wider than on Windows (18 px on an 860 px
label at 100 px). It also drops the
pair before U+00B4 ACUTE ACCENT (`i´`), which may break before it.

**What a page can do:** `word-break: keep-all` removes the opportunities between CJK characters, and
WebKit then kerns as Edge does: every string and label measured apart in Safari and WebKitGTK comes
out as Edge's with it (`probe/v1_0/remedies.py`). It also changes where Japanese and Korean lines may break, so it
suits text that does not wrap (labels, buttons, menu items, headers), not running text.

## Firefox's `font-kerning: auto`

Firefox's `font-kerning: auto` turns kerning off for CJK, and under `lang="ko"` and `lang="ja"` for
some Latin pairs. Since package 0.9.0 every text face asks for kerning in its `@font-face`
(`font-feature-settings: "kern" 1`), so Firefox kerns as Edge does. A page's own `font-kerning:
none` still turns it off.

## Safari only (Core Text)

- No automatic fractions: `1⁄2` with U+2044 FRACTION SLASH is three glyphs at full size, where
  HarfBuzz and DirectWrite make a fraction. **What a page can do:** write the fraction as a single
  character (`½`) where there is one, or ask for it with `font-variant-numeric: diagonal-fractions`
  on just the fraction, which Safari then lays out at Edge's width (every fraction measured alone,
  `probe/v1_0/remedies.py`). On a run with other figures it would turn them into fractions too.
- A combining kana sound mark (U+3099, U+309A) after a character it does not compose with, or a
  combining mark with no base, is as wide as its ink reaches left of its origin (a third of an em for
  U+3099), where Edge gives it none. **What a page can do:** write the composed
  character (`が`, not `か` + U+3099).

## Where the fonts do not draw

- A character no face of the family maps falls to the system's fonts, which differ by system. The
  Latin family (`Harena UI`) has no CJK: put `Harena UI J` in the stack for text that may hold any.
- Default ignorables the fonts do not map (U+034F, U+200C, U+200D, U+2060) are left to the engine,
  which may split the run there, and a combining mark after one may be placed apart from its base.
- U+3164 HANGUL FILLER is 1000 units wide in WinUI 3 and nothing in Safari and Firefox, which treat
  it as a default ignorable.
