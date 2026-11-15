# Plan

The living plan. Decisions marked **locked** carry their rationale; everything else is open.
Versions have one goal each, and the next does not start until the current one is met.

## What this builds

A redistributable UI typeface that stands in for Segoe UI Variable and Segoe Fluent Icons where
those are absent. Shapes come from open fonts; geometry comes from Segoe, measured. A layout sized
under Segoe comes out the same size under this font.

## Families

| family | covers | shapes from | geometry target |
|---|---|---|---|
| **Harena UI** | Latin, Greek, Cyrillic, Hebrew, punctuation, symbols | Open Sans ([ADR 0002](docs/adr/0002-the-latin-source-is-open-sans.md)) | Segoe UI Variable as Edge draws it — advances, kerning, vertical metrics, per named instance ([ADR 0001](docs/adr/0001-the-target-is-segoe-as-the-browser-draws-it.md)) |
| **Harena UI J** | Harena UI, plus Hangul, Kana and Han | Latin as Harena UI; CJK from Pretendard JP ([ADR 0003](docs/adr/0003-the-cjk-source-stays-pretendard-jp.md)) | Latin as Harena UI; CJK at WinUI 3's widths in each language ([ADR 0005](docs/adr/0005-cjk-takes-winui-3s-widths.md)) and Malgun Gothic / Yu Gothic bodies and stems |
| **Harena UI Icons** | Segoe Fluent Icons' code points | Fluent UI System Icons | Segoe Fluent Icons' ink boxes |

**Locked — Harena UI and Harena UI J are separate families.** Segoe UI Variable has no Hangul or
Kana; on Windows they fall back to another face. Keeping the Latin family Latin-only gives it a
single target (Segoe) and a small install. The CJK half matches a different target, the fallback
faces (ADR 0001), so its gate is a different gate.
*Rejected:* one family carrying everything, which is several megabytes to install for a Latin
user and mixes two targets in one gate.

**Locked — one CJK cut, Japanese glyph forms, named J.** Pretendard JP draws Japanese forms. A
Korean UI shows Han rarely enough that a second, Korean-form cut is not worth its size; the
suffix follows Harena Term J and leaves room for a K cut if evidence ever asks for one. Unlike a
terminal, a UI renderer reaches `locl`, so a later K cut could also be a feature rather than a
family.
*Rejected:* "Harena UI CJK" (long, and claims Chinese coverage Pretendard JP does not have).

**Locked — Harena UI J is a superset of Harena UI.** It installs and works alone, as Harena Term J
does. On the web both are served from the same Latin chunks, so the superset costs nothing there.

**Locked — the icon family is "Harena UI Icons".** It mirrors how Segoe UI Variable and Segoe
Fluent Icons are two families: a CSS or XAML stack names the text face and the symbol face
separately, so this font slots in after each. The name says which project it belongs to and what
it pairs with. It avoids "Fluent" and "Segoe", which are Microsoft's names.
*Rejected:* "Harena Icons", which reads as a general icon set rather than the counterpart of a UI
text face. *Rejected:* carrying the icons inside Harena UI, because Private Use Area code points
mean different things in different fonts, and 1,500 icons would add size and gate scope to the
text face.

## Licence — locked

As Harena Term: fonts under OFL 1.1, scripts under Apache-2.0. Upstream Reserved Font Names:
Pretendard JP reserves "Pretendard JP"; Open Sans reserves none. Fonts measured but not used as
sources: Noto Sans CJK reserves "Source", and Selawik reserves "Selawik". No Harena name contains
a reserved name.

Segoe is used only as measured numbers. No Segoe outline, file or table dump enters the
repository (Liberation and Carlito precedent).

**Locked — no Harena name is reserved** (v0.6). OFL 1.1 forbids a modified version to use a Reserved
Font Name, and the OFL FAQ counts subsetting a web font as modifying it. A UI face is subset by the
sites and tools that serve it, so a reserved "Harena UI" would make each of them rename it, and a stack
naming "Harena UI Text" would stop finding their copy. `OFL.txt` therefore carries Harena's copyright
with no reservation, and the upstream notices with Pretendard JP's. *Rejected:* reserving "Harena UI"
as Harena Term reserves its name: a terminal font is installed whole, a UI web font is not.

## Roadmap

| version | one goal |
|---|---|
| **v0** ✓ | Know, with numbers, whether spacing alone can bring Pretendard JP's Latin to Segoe UI Variable's widths. Answered in `docs/v0-feasibility.md`; ADRs 0001–0003 |
| **v0.1** ✓ | One static Harena UI instance (Text, 400) whose string widths match Segoe within tolerance, behind an automated gate. Closed 2026-10-30: gate passes, and in Edge on Windows all 589 browser measurements (canvas and DOM at 12–1000 px) are within 0.000% of Segoe |
| **v0.2** ✓ | Every face Edge can draw from Segoe UI Variable — Small, Text and Display, each at Light, Semilight, Regular, Semibold and Bold — as a static Harena UI face matched to it, behind the same gate. Closed 2026-10-30: gate passes over all fifteen faces; in Edge on Windows, 17,115 measurements are within 0.1% of Segoe, six Small-face DOM ones within one layout unit instead (item 4) |
| **v0.3** ✓ | Every OpenType feature and language a browser can request lays each face out at Segoe's widths: the features Segoe has are matched, the ones it lacks are removed. Closed 2026-10-31: gate passes from a fresh clone, and in Edge on Windows 4,505,220 measurements are within 0.1% of Segoe, 742 Small-face DOM ones within one layout unit instead. Coverage is left out and counted: marks Open Sans lacks, including `i`, `j` and `ị` before CGJ |
| **v0.4** ✓ | In all fifteen faces, Harena UI J lays out Hangul, kana and Han at the widths Edge gives them under a Segoe stack, for each language a page can set, with its Latin identical to Harena UI. Closed 2026-10-31: gate passes from a fresh clone, and in Edge on Windows 10,940,956 measurements are within tolerance, 63,570 of them only by allowing the whole pixel Windows gives a character it emboldens in Semibold and Bold at 20 px and below. What cannot or need not match is left out and counted (the Locked notes); Japanese line boxes stay short until v0.6 |
| **v0.5** ✓ | Harena UI Icons |
| **v0.6** ✓ | Delivery: a page that loads the package's stylesheet and names Harena UI after Segoe lays out as under Segoe, line boxes included, and fetches only the files its text uses. Closed 2026-11-03: gate and mutations pass from a fresh clone; in Edge on Windows 880,110 widths equal the TTFs', and 1,745,100 line boxes equal Windows' with no language beyond the counted characters |
| **v0.6.1** ✓ | A Japanese page fetches its common kanji in one file, and Harena UI J's lines are Segoe's height in every language, as WinUI 3 draws them. Closed 2026-11-04: gate and seventeen mutations pass from a fresh clone; in Edge 880,380 widths equal the TTFs', and all 1,745,100 J line boxes are Segoe's |
| **v0.7** ✓ | Harena UI J lays out CJK at the widths WinUI 3 gives it in each language, not Edge's (ADR 0005). Closed 2026-11-04: gate and eighteen J mutations pass from a fresh clone; in Edge 872,550 code point widths are WinUI 3's, 735 labels agree with WinUI 3 within 0.014 px, and under `ja` no pair is trimmed beyond 450 counted pairs no text writes |
| later | Icons outside WinUI's `Symbol` that lose a state or read as something else, and Trim and Reshare (v0.5's *Later*) |
| **1.0** ✓ | In every engine Harena runs on, and in Chrome and Firefox on macOS and Linux, a page with the package lays out as on Windows: widths, line boxes and fetches. Closed 2026-11-15: gate and mutations pass from a fresh clone; in Safari, WebKitGTK, and Chrome and Firefox on macOS and Linux, every width, line box and fetch is Edge's on Windows or a counted kind within its bound (item 6), and what a page can do about each is `docs/engines.md` |

Each version's spec is written when the previous one closes. The closed ones follow, newest
first.

## 1.0 — the package on macOS and Linux, as on Windows (closed 2026-11-15)

**Goal.** In every engine Harena runs on, and in Chrome and Firefox on macOS and Linux, a page with
the package lays out as on Windows: widths, line boxes and fetches.

**Why.** Every measurement so far was taken in Edge on Windows. Harena is a Tauri app, so it draws
with the platform's web view: WebView2 on Windows (Edge's Blink, verified), WKWebView on macOS
(WebKit, shaping through Core Text) and WebKitGTK on Linux (WebKit, shaping through HarfBuzz).
winui-svelte also runs in ordinary browsers. None of these has Segoe, so each draws Latin from
Harena UI and CJK from Harena UI J, and each may treat what the fonts encode differently: whether
Core Text applies `dist` under Japanese, which vertical metrics an engine builds `line-height:
normal` from, whether `unicode-range` splits a cluster as Blink does.

**Locked — the engines** (owner, 2026-11-04). Required: WebKit on macOS (Safari, standing for
WKWebView: the same WebKit and Core Text), WebKitGTK on Linux (the distribution's `webkit2gtk-4.1`,
the library Tauri links, driven through its own browser), and Chrome and Firefox on both. Edge on
Windows is the reference and was verified through v0.7.
*Rejected:* Playwright's WebKit build on Linux, which is not the library Tauri loads. *Later:* a
WKWebView harness inside a Tauri build, if Safari passes and the app is ever seen to differ; Chrome
and Firefox on Windows.

**Locked — where.** macOS: a macOS guest in UTM (Apple's virtualization) on the owner's Mac, signed
in, reached over SSH on the tailnet, recorded by macOS and browser versions and device pixel ratio;
layout is Core Text's on the CPU, whatever the guest's display. Linux: an Ubuntu 24.04 LTS guest with the desktop's default fonts (Noto CJK among
them, so a missed fallback shows), the distribution's WebKitGTK, Firefox and Chrome. Neither has
Segoe.

**Locked — one probe, through WebDriver.** Each engine is driven by its W3C WebDriver
(`safaridriver`, `WebKitWebDriver`, `chromedriver`, `geckodriver`), running the same measuring
script in the same page from the repository's file server; Edge, the reference, runs the script
over CDP as before. The script measures in layout units and returns numbers only.
*Rejected:* a page that posts its results, which needs a person at each run.

**Locked — the reference.** For a page that names Harena after the Segoe stack, the reference is
what Edge on Windows lays out with Segoe installed: Latin from Segoe, CJK from Harena UI J. Widths
are compared within v0.3's tolerance (0.1%, or one layout unit for a short string), CJK and labels
against `data/v0_7` and WinUI 3 within v0.7's; line boxes are compared exactly, after each engine's
own rounding is recorded.

**Items**

1. **Rig.** The Linux guest and the Mac reachable, each engine's driver running, versions recorded;
   the file server reachable from both.
   *Done when:* a one-line script returns the engine and version from each of the six.
   *Done* 2026-11-09: each of the six opened a WebDriver session and loaded `probe/page.html` from
   the host's file server. macOS 27.2 (arm64, English only, device pixel ratio 2): Safari 27.2 with
   its `safaridriver`, Chrome 157.0.8103.39 with chromedriver 157.0.8103.38, Firefox 159.0.1 with
   geckodriver 0.37.1. Ubuntu 24.04.5 (GNOME on Wayland, `en_US.UTF-8`, `fonts-noto-cjk`, device
   pixel ratio 1): `libwebkit2gtk-4.1-0` 2.52.6 through its MiniBrowser and `WebKitWebDriver`, Chrome
   157.0.8103.38 with its chromedriver, Firefox 159.0.1 (the snap) with its geckodriver. Chrome and
   Firefox update themselves, so each run records its versions.
2. **Probe.** `probe/v1_0/`: one measuring script (widths, line boxes, fetches) and a driver for each
   protocol; the reference taken in Edge with the same script.
   *Done when:* Edge's run of it reproduces v0.6.1's and v0.7's Edge numbers.
   *Done* 2026-11-09: `probe/v1_0/collect.py` measures every part in one engine into one file, through
   CDP or WebDriver, from `probe/v1_0/serve.py` (the probe's files only, never cached);
   `probe/v1_0/check_edge.py` runs v0.6.1's and v0.7's checks on Edge's. In Edge 151 (6 minutes):
   of 880,380 widths, 880,353 are the whole TTFs' and 27 are counted (below); 1,745,190 line boxes
   are Segoe's (now with `A` in J's Latin),
   the nine pages fetch as before, 872,550 code points are WinUI 3's, 735 labels agree with WinUI 3
   within 0.014 px, and 887,770 pairs are trimmed by nothing beyond the 450 counted. Two things the
   first run found are settled (item 6):
   - *WinUI 3's no-language default* (ADR 0005, amended). Re-measured with v0.7's app and cases on a
     fresh guest, and checked on winui-svelte's reference guest, WinUI 3 with no `Language` lays CJK
     out as under `ja-JP` (`あ` 81.6 px at 100 px), not as under `ko-KR` as v0.7's guest did (100).
     `data/v1_0` holds the new widths and pairs; J 0.8.0 takes its default from them and adds `KOR`
     with `ko-KR`'s under `dist`. This changes Edge on Windows, deliberately: a page with no `lang`
     now lays Japanese out as WinUI 3 does. The labels' WinUI 3 widths are `data/v1_0/labels.json`.
   - *Counted: conjoining jamo.* `가`, `각` and `한글` written as conjoining jamo are 27 of the widths:
     J maps no conjoining jamo, so the package leaves them to the system's fonts, while the whole TTF
     composes them into the syllable J has (1020 per syllable in Semibold against 1000). The same
     class as v0.7's counted pairs; WinUI 3 composes neither, drawing each jamo a full em.
   Resource Timing lists no font files in WebKitGTK, so item 5 observes fetches at the server.
   *Lesson:* an engine keeps fonts it fetched in an earlier run: before the cache was off, Edge laid
   out J 0.7's files under J 0.8's names.
3. **Widths.** In each engine: the v0.3 and v0.4 strings in every Harena UI and Harena UI J face, in
   no language, `ko` and `ja`; every J code point alone in each language; the v0.7 labels; Harena
   UI Icons' code points. Against the reference.
   *Done* 2026-11-10, on package 0.9.0: `probe/v1_0/check_engines.py` passes for all six (below).
4. **Line boxes.** In each engine, v0.6.1's lines: `A` alone and `A` with each J code point, at 14
   and 40 px, in each face and language, with the package after the Segoe stack. Against Segoe's on
   Windows.
   *Amended while measuring* (owner, 2026-11-10): a line at `line-height: normal` is the ascent and
   descent each rounded by the engine's own rule, and Blink's rounds to the device pixel, so the
   reference is Edge at the engine's display scale: Segoe's 14 px line is 19 px at 100% and 18.5 px
   at 200% (Edge started with `--force-device-scale-factor=2`; CDP's emulated scale does not round
   so). Each engine's rule is recorded in `check_engines.py` and checked to give its every line.
   *Done* 2026-11-10: Chrome's lines are Segoe's at both scales, WebKit's at 1x; the rest counted.
5. **Fetches.** In each engine, v0.6's nine pages: each fetches exactly the files Edge fetches.
   *Amended while measuring* (2026-11-10): where a page names Segoe first, an engine without it also
   fetches the package's file that stands in for Segoe; "exactly" holds for every other file.
   *Done* 2026-11-10: observed at the server (`serve.py --log`, `fetches.py`, a session per page:
   Firefox otherwise keeps a font an earlier page fetched), judged by `check_fetches.py`. Edge's are
   v0.6's at the server and in Resource Timing alike; each engine's are Edge's, and where a page
   names Segoe first, the package's file standing in for it, fetched even for text with no Latin,
   since the line's height comes from the family's first available font.
6. **What differs is decided, then fixed or counted.** A difference found in 3–5 is reported with
   its cause before anything changes. A fix to the fonts or stylesheets must leave Windows as it is,
   proved by re-running the v0.7 gate and Edge probe; what is not fixed is counted, with its cause,
   in this section.
   *Done when:* 3–5 hold in every engine, with what does not counted here.
   *Done* 2026-11-10. First measured: Safari 27.2 (macOS 27.2, 2x), Chrome 157.0.8103.39 (macOS,
   2x), Firefox 159.0.1 (macOS, 2x); WebKitGTK 2.52.6, Chrome 157.0.8103.38, Firefox 159.0.1 (Ubuntu
   24.04.5, 1x); against Edge 151 at 1x and 2x (re-measured at the close: Result). Edge's widths at
   2x are its 1x's within two layout units.
   - *Fixed: Firefox's `font-kerning: auto`* drops kerning for CJK, and under `ko` and `ja` for
     pairs of accented capitals (`ÀÇ`). Package 0.9.0 declares `font-feature-settings: "kern" 1`
     in every text face (`scripts/build_css.py`, required by `verify_web.py` W4, broken by
     `mutate_web.py`'s `unkerned`); Firefox then kerns as Edge does. Windows is unchanged:
     `check_edge.py` passes on 0.9.0 as on 0.8.0.
   - *Counted*, each a kind in `check_engines.py` that holds only at the width its cause predicts or
     within the bound it sets, as each says (a counted difference outside it is a fault); only
     `fallback`, and `ignorable` in WebKit, where the system's fonts draw, are unbounded. Widths are
     compared within 0.1% or one of the engine's layout units, as locked. What a page can do is
     measured in each engine by `remedies.py`:
     - `break` (WebKit): WebKit measures text in pieces at each line-break opportunity, so a kern
       pair across one (between CJK characters, before U+00B4) is lost: 11,055 pairs, 255 widths
       and 42 labels in each WebKit (labels at most 2.1% wide). Each lies between Edge's width and
       its glyphs' advances, and measured again in the engine with `word-break: keep-all` is Edge's.
     - `coretext` (Safari): no automatic fraction at U+2044 (a fraction alone, measured again with
       `font-variant-numeric: diagonal-fractions`, is Edge's; among other figures, which that would
       turn too, it is bounded by its glyphs' advances); a combining sound mark that composes with
       nothing before it is exactly as wide as its ink left of the origin where it is alone or first
       before a letter, and otherwise wider by no more than the marks' ink, a bound, not a
       prediction (Core Text places it by rules the probe does not model): 9,222 widths, 90 code
       points, 6,019 pairs.
     - `rounding` (WebKit, Gecko): Safari rounds to the CSS pixel (19 at 14 px, where Edge at 2x
       gives 18.5); Firefox rounds up to the device pixel (20 and 55 at 1x, 19.5 and 54 at 2x,
       against 19 and 53). Every line is its engine's rule's. A `line-height` in px is that height in
       every engine (20 px for 14 px text, 52 px for 40 px, every J code point, each size and language).
     - `fallback`: a character no face of the family maps is drawn by the system's fonts, which
       differ by system; unbounded, since no font of ours sets the width.
     - `ignorable`: an unmapped default ignorable is left to the engine. Blink and Gecko keep the run
       whole and give Edge's package; WebKit splits the run there and draws what follows from the
       system's fonts, unbounded as `fallback` is. U+3164, which J maps, is nothing wide alone in
       Safari and Firefox, a default ignorable to them.
     - `segoe`: 60 widths in which Edge's package is off Segoe in Edge itself (bare combining
       marks, a letter before CGJ); Chrome, Firefox and WebKitGTK give Edge's package there, and
       Safari, whose bare marks are `coretext`, gives the rest.
   What a page can do about each is `docs/engines.md`, for the package's consumers.
   *Lesson:* a macOS guest whose screen saver runs is a locked session to Safari, which then lays
   out a hidden page and runs its timers at a crawl: a measurement took minutes, not seconds.

**Out of scope.** The repository's layout at release, including joining Harena Term's font under
one `harena-hq/fonts` repository: decided at release. Publishing to npm: after 1.0. Chinese and
vertical text, as before.

**Result** (2026-11-15). Spec 2026-11-04, approved 2026-11-09.

- *Files.* Harena UI J 0.8.0 (no language at WinUI 3's widths, `KOR` at Korean's), Harena UI Icons
  0.5.2 (its three key labels set in J 0.8.0), package 0.9.0 (every text face asks for `kern`): 196
  WOFF2, 31.9 MB.
- *Gate.* From a fresh clone, `verify.py`, `verify_j.py`, `verify_icons.py`, `verify_web.py` and
  `build_css.py --check` pass, the four `SHA256SUMS` files match, and `mutate_icons.py`,
  `mutate_j.py` and `mutate_web.py` catch all their mutations (19, 20 and 18).
- *Engines* (re-measured on Icons 0.5.2): Edge 151 at 1x and 2x on Windows 11 25H2; Safari 27.2,
  Chrome 157.0.8103.51 and Firefox 159.0.1 on macOS 27.2 (2x); WebKitGTK 2.52.6, Chrome
  157.0.8103.38 and Firefox 159.0.1 on Ubuntu 24.04.5 (1x). `check_edge.py` passes;
  `check_engines.py` passes 48 checks in six engines with no fault, each counted kind at the counts
  item 6 gives; `check_fetches.py` finds each engine's nine pages Edge's.
- *Code review.* Codex, in four rounds on the probe and its data, found a probe that could measure
  before a subset loaded or record fetches before layout, resumes that mixed engines, packages and
  malformed runs, checkers that passed on empty results, a server whose directory indexes bypassed
  its symlink check, and gates in J and WinUI's data that a changed value could pass; at the
  milestone, Codex and an adversarial critic agent found counted kinds that accepted widths their
  cause did not predict, a tolerance wider than the one locked, an emptied `dist` that check 16 no
  longer caught, and lines not held to their engine's rule. All fixed; Codex's review of the fixes
  found none left.
- *Lesson:* Harena UI Icons is built from J, so changing J rebuilds the icons: 1.0 left `dist/`'s
  icons built from J 0.7.0, which the working tree's gates matched, and only the gates from a fresh
  clone caught it.
- *Lesson:* Chrome updates itself between runs (Chrome on the Mac went from 157.0.8103.39 to .51
  during the last one), so each file is bound to the engine that measured it, and `collect.py` and
  `check_engines.py` refuse to mix them.

## v0.7 — Harena UI J at WinUI 3's CJK widths (closed 2026-11-04)

**Goal.** In every face and language, Harena UI J lays out Hangul, kana and Han at the widths
WinUI 3 gives them, not Edge's.

**Why the target moves** (owner, 2026-11-04). ADR 0001 took Edge's CJK fallback widths, rejecting
WinUI's because a page on Windows would then differ from the same page without the font. Since v0.6
that page draws CJK from Harena UI J anyway, and since v0.6.1 its lines are WinUI's height: winui-svelte
reproduces WinUI, and Edge's own fallback is no longer anything a page shows. ADR 0005 records the
change; ADR 0001 stands for Latin.

**What WinUI does** (explored 2026-11-04 in WinUI 3 Gallery's ScratchPad on the second guest, widths
by UI Automation at 100 px, whole pixels):

| at 100 px | no `Language` | `ko-KR` | `ja-JP` |
|---|---|---|---|
| あ, ア (Regular) | 100, 100 | 100, 100 | 82, 78 |
| 「, 」 | 58 | 58 | 50 |
| 、, 。 | 100 | 100 | 67 |
| ー | 65 | 65 | 65 |
| Han, Hangul, （）, Ａ | 100 | 100 | 100 |

- With no `Language` WinUI draws as under `ko-KR` (the Gallery's language is `en-US`, as is the
  guest's); under `ja-JP`, as Yu Gothic UI, whose kana are proportional and whose punctuation is half
  or two-thirds width. Edge drew those at 1 em and trimmed pairs by `halt`, which WinUI does not.
- Bold widens the kana a little (あ 84 under `ja-JP`) and nothing else sampled.
- UI Automation gives whole pixels, and only for what is on screen.

**Locked — WinUI's widths measured exactly, by a WinUI 3 app** (amended 2026-11-04, before the
probe). `probe/v0_7/measure` is a WinUI 3 app, built against the Windows App SDK the Gallery ships
(2.5.4-experimental), that lays each case out as a `TextBlock` in the default style
(`XamlControlsResources`), unrounded, and writes its `ActualWidth`. That is the width WinUI lays out,
exact (`ja-JP` あ is 81.591796875 px at 100 px, 1671/2048 em); the Gallery's whole pixels are the same
widths rounded up by layout rounding, and the app gives every width the exploration measured, so
rounded. The data is built from directly.
*Rejected:* identifying the faces WinUI draws with from the Gallery's whole pixels and reading their
advances from the files, as first specified: the app gives the widths themselves, needs no candidate
list, and takes seconds where the Gallery's editor took minutes per few hundred characters.

**Locked — per-language widths as v0.4 encodes them.** The `hmtx` advance is WinUI's with no
language; single adjustments under `JAN`, in `dist`, give `ja-JP`'s where they differ, and each
language's pairs WinUI lays out apart from their parts are its `kern` (amended 2026-11-04, after the
probe: `ko-KR` lays out as no language in every case, so it needs no `KOR`, and `dist` is the one
width feature kept, as a page cannot turn it off). A glyph whose advance narrows keeps its ink where
WinUI's face has it: centred for kana and Han, at its side for punctuation (v0.4's rule for halved
punctuation). v0.4's `halt` and its per-script run widths, which reproduced Edge, are removed, as are
`KOR`, `ZHS` and `ZHT`; Edge has nothing to trim by (`text-spacing-trim`).

**Locked — a composing kana and mark is the composed letter.** HarfBuzz composes a kana and
U+3099 or U+309A into the letter Unicode composes them to, when the font has it, as Chromium does; no
font can stop it. WinUI lays five such pairs out apart with no language (`ゔ` as `う` and the mark,
100 px against 76.7) and three under `ja-JP` differently. The gate takes the composed letter's width
for them; text is normally precomposed.

**Locked — every weight measured.** WinUI picks a face per weight; J's five weights each take the
widths WinUI gives at the same weight.

**Items**

1. **Probe WinUI.** `probe/v0_7/`: per language (none, `ko-KR`, `ja-JP`) and weight, every J code
   point outside Harena UI at 100 px, by the app. Data in `data/v0_7/winui.json`: widths in px, and
   the provenance.
   *Done when:* every code point has a width in each language and weight, and the app's widths, rounded
   up, are the Gallery's for every case of the exploration.
2. **Pairs.** Pairs of J code points, from the v0.4 sentences and each class's neighbours (kana, Han,
   Hangul, punctuation), measured by the app against the sum of their parts in each language.
   *Done when:* kerning or trimming between CJK characters is either absent or recorded.
3. **Build.** `build_j.py` takes `data/v0_7` for CJK widths, drops `halt`, `KOR`, `ZHS` and `ZHT`,
   gives `JAN` its widths in `dist`, and moves ink as locked. J becomes 0.7.0, the package 0.7.0.
4. **Gate.** `verify_j.py`: every code point's advance under each language, with `kern` off, and
   every measured pair's, equals its width in `data/v0_7`; every script has only no language's
   system and `JAN`, with Harena UI's features and no required feature, `dist` only under `JAN` and
   the same in every script, and no other width feature; only `kern` and `dist` gain lookups, glyph
   pairs of advance alone and single adjustments, touching only CJK; each glyph's ink sits where the
   locked rule puts it, by default and under `JAN`. `scripts/mutate_j.py` proves the three
   checks catch what they claim. `verify_web` unchanged.
5. **In Edge and WinUI, to close.** Every J code point in each face and language, in Edge with the
   package, at 1000 px, equals its `data/v0_7` width; a set of labels (kana, Han, punctuation and
   mixes, the v0.4 sentences) measured in WinUI at 100 px and in Edge at 100 px are equal within one
   pixel; and under `ja` Edge trims no pair.
   *Done when:* all three hold, with what does not counted here.

**Out of scope.** WinUI's own Latin line rounding (38 and 54 px at 28 and 40 px, against Edge's 37 and
53): winui-svelte's. A Windows display language other than English, which may change WinUI's choice
with no `Language`: recorded as measured on `en-US`. Chinese and vertical text, as before.

**Result** (2026-11-04).

- *WinUI 3* (the app on the second guest, Windows App SDK 2.5.4-experimental, 100% scale): 290,865
  widths, 19,390 code points in three languages and five weights, every one of the Gallery's 96
  rounded up as it gives them; 2,663,310 pair widths, 177,554 pairs per language and weight. `ko-KR`
  lays out as no language throughout. Under `ja-JP`, 183 code points take other widths, and 1,702
  pairs at Light and 2,682 at the other weights kern; with no language, two pairs differ, both a kana
  and a sound mark.
- *Files.* J 0.7.0, Icons 0.5.1 (two key labels set in J's new widths), package 0.7.0: 196 WOFF2,
  31.9 MB.
- *Gate.* `verify.py` passes; J's checks 15–17 hold 592,281 widths and pairs per face to `data/v0_7`
  with `kern` off for single code points, and every glyph's ink where the rule puts it.
  `mutate_j.py` catches all eighteen mutations, `mutate_web.py` its seventeen.
- *In Edge* (Edge 151 on the guest, `probe/v0_7/browser.py`): 872,550 code point widths at 1000 px
  are `data/v0_7`'s within rounding; 735 labels in WinUI 3 and in Edge agree within 0.014 px; 887,770
  pairs under `ja` are their parts and kern, so Edge trims none. *Counted:* 450 of them, a Hangul
  syllable then a sound mark, which the package keeps in different files, so that Edge draws the
  cluster from Windows, as v0.6.1's mark after a Latin letter; the whole TTF lays them out at their
  parts. No text writes one.
- *Code review.* Codex, in three rounds, found ways a changed font passed the gate: Japanese widths
  moved into `kern`, plainly or made a required feature; class pairs, whose class 0 is every glyph,
  in `kern` or `mark`; ink moved by placement, in a default `kern`, in one script's `dist`, on a
  sound mark, by many small adjustments, or behind a second `JAN` record; and item 3 still said to
  drop `dist`. All fixed: widths are checked with `kern` off;
  check 16 holds the systems to no required feature, every feature but `kern` and `dist` to Harena
  UI's lookups, added ones to glyph pairs of advance alone and to one `dist` shared by every script,
  and each script and system to one record; check 17 reads placement from the outlines and from
  `dist`, one adjustment per glyph; each has its mutation.

## v0.6.1 — Japanese delivery, and WinUI's line height (closed 2026-11-04)

**Goal.** A Japanese page fetches its common kanji in one file, and Harena UI J's lines are Segoe's
height in every language, as WinUI 3 draws them.

**What changed the plan** (owner, 2026-11-04). Its consumers, winui-svelte and the Harena app built on
it, ship Korean, Japanese and English; v0.6 assumed no Japanese consumer, and cut Han in code point
order, so a Japanese page fetched most of seven Han chunks. And WinUI 3, measured on a guest (WinUI 3
Gallery 3.0.4's ScratchPad, sizes by UI Automation), does not let a fallback
face change a line:

| TextBlock, `Language` none, `en-US`, `ko-KR` or `ja-JP` | 14 px | 20 px | 28 px | 40 px |
|---|---|---|---|---|
| `Settings`, `설정`, `設定`, `設定する`, `カタカナ`, `Save 保存`, `「設定」` | 19 | 27 | 38 | 54 |

Button and CheckBox are 32 px with each of those labels in each language. Edge, by contrast, takes a
fallback face's line metrics, which v0.6 reproduced per chunk; winui-svelte's reference is WinUI.
WinUI's 38 and 54 against Edge's 37 and 53 for Segoe itself, at 28 and 40 px, is how each rounds a
line, not a font's; it is winui-svelte's to handle. WinUI also gives some CJK other widths than Edge
(`カタカナ` 120 px at 40 px under `ja-JP` against 160): v0.7.

**Locked — JIS X 0208 level 1 is one chunk, tried first for Han.** 2,965 characters, nearly every
kanji in common use, about 450 KB per face, declared over the whole CJK Unified Ideographs block and
last, as KS X 1001's chunk is over Hangul. The rest of Han stays in parts in code point order. A
Japanese page then fetches its Latin face, kana (24 KB) and this chunk: about 520 KB per face, where
v0.6 fetched about 1.3 MB. The 256 KB cap was a choice, not a measurement, and gives way here: the
common set in one file is the point. *Supersedes* v0.6's amendment that cut all Han in code point order.

**Locked — no line metrics overrides.** Every J chunk keeps the file's metrics, Segoe's (v0.4), so a
line holding CJK is Segoe's height in every language, as in WinUI. *Supersedes* v0.6's "CJK line boxes
on the web are Windows'". `data/v0_6/fallback.json` and its probe stay as the record of what Edge
does on its own; nothing reads them now.

**Items**

1. **Chunks and stylesheets.** `build_web.py` cuts `han-1` (JIS level 1) and the rest of Han in parts;
   `build_css.py` declares no overrides.
   *Done when:* every chunk but `han-1` is under 256 KB, and `j.css` stays short.
2. **The gate.** W4: no face declares an override. Its mutations follow: an override added to a chunk
   fails W4.
   *Done when:* `verify_web.py` and `mutate_web.py` pass from a fresh clone.
3. **In Edge.** `probe/v0_6/browser.py`: widths as in v0.6; line boxes: with J after the Segoe stack,
   every J code point outside Harena UI after `A`, at 14 and 40 px, in each face, with no language and
   under `ko` and `ja`, is the height of `A` alone; fetches as in v0.6, plus a Japanese page, which
   fetches kana and `han-1` only, and a rare kanji, which adds the one part holding it.
   *Done when:* all hold, with no exceptions.
   *Amended while measuring:* the two combining voicing marks, U+3099 and U+309A, are measured after
   `Aか`. Straight after a Latin letter, the mark and its base are in different files of the split
   family, Edge cannot draw the cluster from one face, and takes it from Windows' fallback, which is
   taller under `ja` (60 measurements over fifteen faces and two sizes, all these two marks). No text
   writes a kana voicing mark after a Latin letter; after kana, its base, it is drawn from J.
4. **WinUI's measurement** kept as a probe, `probe/v0_6_1/`, and the package version 0.6.1.

**Result** (2026-11-04).

- *Files.* 196 WOFF2, 31.9 MB in the package: twelve chunks per J face. JIS level 1 is 449 KB in Text
  Regular (465 KB at most); every other chunk is under 256 KB. `j.css` is 59 KB, 2.2 KB under gzip,
  with no override.
- *Gate.* `verify_web.py` passes, 16 checks; `mutate_web.py` catches all seventeen mutations.
- *In Edge* (Edge 151 on the guest): 880,380 widths equal the whole TTFs'; 1,745,100 line boxes,
  every one the height of `A` alone, with the two voicing marks after `Aか`; nine pages fetch exactly
  what was expected, among them a Japanese one (kana and JIS level 1) and one with `鬱` (and the one
  part that has it).
- *WinUI 3* (WinUI 3 Gallery 3.0.4 on a second guest of the same build, 100% scale): the table above,
  168 bounds in `data/v0_6_1/winui-text.json`.
- *Code review.* Codex, FIX-FIRST: W4 read only the declarations its pattern recognized, so
  `Ascent-Override:120%` passed it; the voicing marks' base was changed without the spec saying so;
  Hangul's common chunk was exempt from the size cap too, which the spec gave JIS level 1 alone. All
  fixed: W4 reads every declaration as CSS does, with a mutation in that form; the amendment is in
  item 3; only `han-1` is exempt.

## v0.6 — delivery: the web package (closed 2026-11-03)

**Goal.** A page that loads the package's stylesheet and names Harena UI after Segoe lays out as it
does under Segoe, line boxes included, and fetches only the files its text uses.
*Amended 2026-11-03:* the spec first added "and on Windows draws what it drew without the package";
the measurement below showed `local()` cannot do that, and the owner dropped it (the Locked note).

**What the delivery starts from** (explored 2026-11-03 on the v0.5 build).

- **Sizes.** As WOFF2, a Harena UI face is 49 KB, Harena UI Icons 156 KB, and a whole Harena UI J face
  1.92 MB: fifteen J faces would be 29 MB, which is why J is split and the others are not.
- **What a split may not cut.** A font file is shaped alone, so a layout rule whose glyphs fall in two
  files stops applying. Joining every glyph that any GSUB or GPOS rule of J Text Regular reads together
  gives three kinds of group: Harena UI's 1,010 code points, tied to nothing outside them; one group of
  231 kana and full-width punctuation (the kana `kern`, `dist` and the contextual `halt`); and 19,383
  code points tied to nothing, among them every Hangul syllable and every Han character.
- **Standard sets slice the rest.** Of J's 19,390 code points outside Harena UI, 11,172 are Hangul,
  2,350 of them in KS X 1001 (172 KB as one file, the rest 519 KB); 7,140 are Han, 2,965 in JIS X 0208
  level 1 (448 KB) and 3,390 in level 2 (597 KB); 1,078 are kana and symbols. Python's own `euc_kr`
  and `euc_jp` codecs give these sets, so no frequency list is needed.
- **winui-svelte names the optical size in the family** (its ADR 0003): `"Segoe UI Variable Small"`,
  `"Text"` or `"Display"` per ramp step, then `"Segoe UI"`, then its own `'winui-svelte text'` face.
  The Harena UI names already follow it: typographic families `Harena UI Small`, `Text`, `Display`,
  `Harena UI J Small` and so on, and `Harena UI Icons`.
- **On Windows a stack falls back per character, in order.** Segoe covers all of Harena UI's and Harena
  UI Icons' code points, so neither is fetched or drawn there. It covers no Hangul, kana or Han: a stack
  naming Harena UI J draws those from J instead of from Windows' own fallback faces, at Windows'
  widths (v0.4) in Pretendard JP's shapes.
- **Which face Windows falls back to depends on the language** (measured in Edge on the guest with
  DevTools' platform fonts, under a Segoe stack). Hangul is always Malgun Gothic. Kana is Yu Gothic with
  no language and under `ja`, Malgun Gothic under `ko`. Han and CJK punctuation are Microsoft YaHei with
  no language, Malgun Gothic (MS PGothic in Light) under `ko`, Yu Gothic under `ja`. Light and Semilight
  take each family's light face, Semibold and Bold its bold one.
- **Only Yu Gothic makes a line taller.** At 14 px a line of kana is 22 px where Latin's is 19; Malgun
  Gothic and YaHei lines are Segoe's height, or 1 px more at 40 px and up. Edge takes the line metrics
  as DirectWrite reports them: `win` ascent and descent, with the gap `hhea` adds beyond them, which is
  why Yu Gothic Bold's lines differ from Regular's though `hhea` is the same. J declaring those numbers
  by `ascent-override`, `descent-override` and `line-gap-override` gives Windows' line box at every
  size from 9 to 96 px, for each face against the text Windows draws in it.

**Locked — the CSS family names are the installed names.** A page names `"Harena UI Text"` whether the
font is served or installed, and a stack is written once. *Rejected:* one web family with `opsz` picked
by weight or descriptor, which no consumer's stack names.

**Locked — Harena UI and Harena UI Icons ship one WOFF2 per face; Harena UI J ships its CJK in chunks
and its Latin from Harena UI's files.** Each J face is declared as Harena UI's file for Harena UI's code
points plus its chunks, each under its own `unicode-range`. The chunks are, per face: kana with CJK
and full-width punctuation (the tied group is inside it); the other symbols; Hangul in KS X 1001, with
the compatibility jamo; the rest of Hangul, in three parts; Han, with radicals and compatibility
ideographs, in seven parts in code point order. Every chunk is under 256 KB: thirteen per face.
*Amended while building:* the spec cut Han by JIS X 0208 level as Hangul by KS X 1001. Both sets are
scattered in code point order, and J's Han is too (4,287 runs), so their exact `unicode-range`s made
`j.css` 1.38 MB, 470 KB under gzip. A face draws only what its range and its file both have (CSS Fonts
4, §4.5), and of faces whose ranges overlap the last declared is tried first. So each chunk is
declared over the blocks its code points are in, and KS X 1001's chunk, declared last, over every
syllable: a Korean page fetches it, and the chunk of a rare syllable only when one appears. Han has no
such set that spans its range, and is cut in code point order instead: a Japanese page fetches the
Han chunks its text touches, which is most of them, up to 2.0 MB per face used. A character J lacks
inside a Han chunk's range costs that chunk's fetch before the next family draws it. *Trigger to
revisit:* a Japanese consumer, for whom a JIS-sliced stylesheet could be added beside `j.css`.
This serves v0.4's "Latin identical to Harena UI" as shared bytes, and a Korean page fetches its Latin
face and one or two Hangul chunks, about 220 KB. *Rejected:* a whole J face (1.9 MB before any text);
Google Fonts' frequency slicing, which needs a usage corpus this project does not have, and saves
bytes only once evidence shows pages load more chunks than they use.

**Locked — a group no rule may cut is checked, not assumed.** The gate joins glyphs as above for every
face, resolves each code point to the file a browser draws it from, and fails if a group spans two.

**Locked — weights by range, upright only.** Each face is declared for the CSS weights Edge gives its
Segoe instance (`data/v0_2/matching.json`): 1–325 Light, 326–375 Semilight, 376–499 Regular, 500–649
Semibold, 650–1000 Bold, the same in all three optical sizes. Every face is `font-style: normal`, so
italic is synthesized as for Segoe (ADR 0004).

**Locked — `font-display: block`.** A layout drawn first in another face and then moved is the thing this
project exists to prevent. Latin faces are 49 KB. *Rejected:* `swap`, which draws one wrong layout per
load.

**Locked — CJK line boxes on the web are Windows'.** v0.4 kept Segoe's vertical metrics in the file, so
a kana line is 3 px short at 14 px, and Hangul 1 px at 40 px. Each chunk declares, per weight, the line
metrics of the face Windows draws most of its characters with when no language is set: Malgun Gothic
for Hangul and the other symbols, Yu Gothic for kana, Microsoft YaHei for Han (Microsoft JhengHei UI for
one Light part, as measured). The numbers are measured and kept in `data/v0_6/fallback.json`.
winui-svelte's pages set `lang="en"`, which falls back as no language does. A `unicode-range` cannot
depend on `lang`: under `ko` and `ja`, and where Windows draws a character from another face than its
chunk's, the line box can differ, and item 7 counts each such character.
*Rejected:* changing the file's metrics, as v0.4 rejected.

**Locked — J draws CJK on Windows too** (owner, 2026-11-03). Harena UI J named after Segoe takes the
characters Segoe lacks, on Windows as everywhere: at Windows' widths and, with the overrides, its line
boxes, in Pretendard JP's shapes. The layout is the promise, not the faces.
*Rejected:* naming Windows' fallback face first in each chunk, `src: local(…), url(…)`. It was the
spec's first choice, measured before it was built: Windows' face depends on the language, which a
chunk cannot, so under the most common case, no language, Han would draw from Yu Gothic where Windows
draws YaHei and take Yu Gothic's widths and trimming, moving Windows' own layout. Only Hangul, always
Malgun Gothic, could have kept Windows' faces exactly; that can be added later without changing
anything else.

**Locked — the package.** `@harena-hq/ui-font`, as Harena Term's `@harena-hq/term-font`, assembled by a
script from tracked metadata in `npm/` and ignored build output, as Harena Term's `package_npm.py`.
Entries: `ui.css` (Harena UI), `j.css` (Harena UI J, which declares Harena UI's files under its own
names), `icons.css` (Harena UI Icons), and `index.css` importing `ui.css` and `icons.css`. A J page
imports `j.css` and `icons.css`. The stylesheets are generated from data, and the tracked copies must
equal what the generator writes. Licence `OFL-1.1 AND MIT AND Apache-2.0`: fonts, Fluent's outlines,
the stylesheets and scripts. Fonts keep the version that last changed them (Harena UI 0.3.0, Icons 0.5.0;
J becomes 0.6.0 with its copyright string), recorded in `harena.fontVersions`; the package is 0.6.0.

**Items**

1. **Licence.** `OFL.txt` (the text, with Harena's copyright lines), `THIRD_PARTY_NOTICES.md` (Open
   Sans, Pretendard JP with its Reserved Font Name, Fluent UI System Icons' MIT notice), and Harena UI J's
   copyright string with Pretendard JP's reservation, as Harena UI Icons' already carries. A `README.md`
   for the repository and one for the package, with a winui-svelte-shaped stack.
   *Done when:* the files exist, J's name table carries the wording, and `verify_j.py` checks it.
2. **Measure the fallback faces.** `probe/v0_6/`: for each J face and chunk, the faces Edge draws its
   characters with under a Segoe stack with no language and under `ko` and `ja`, by name with glyph
   counts; and each such face's metrics, read from its file on the guest (`metrics.ps1`). Names, counts
   and numbers only, into `data/v0_6/fallback.json`, with the chosen face per chunk and weight.
   *Done when:* every chunk and weight has a face, and J Text with that face's overrides lays out a
   line of the chunk's characters drawn by that face at Windows' height at 9–96 px.
3. **WOFF2 and chunks.** `scripts/build_web.py` writes `dist/web/`, and `SHA256SUMS-Web` pins it. Brotli
   is pinned in `requirements.txt`.
   *Done when:* a second build writes the same bytes; each WOFF2 decompresses to a font whose glyphs,
   advances and layout tables equal the TTF's for its code points.
4. **Stylesheets.** `scripts/build_css.py` writes `npm/*.css` from the chunk table, the weight ranges
   and `fallback.json`.
   *Done when:* regenerating changes nothing, and every `unicode-range` is exactly its file's cmap.
5. **Package.** `scripts/package_npm.py` assembles `build/npm-package/`; `npm pack` makes the tarball.
   *Done when:* the tarball holds exactly the declared files, every WOFF2 matches `SHA256SUMS-Web`, every
   `url()` in every stylesheet names a file in it, and each export resolves.
6. **The gate.** `scripts/verify_web.py`, with mutations as `mutate_icons.py`:
   - **W1 Partition.** Per family and face, the declared ranges cover the TTF's cmap exactly, without
     overlap; J's Latin ranges are Harena UI's, and J's glyphs there equal Harena UI's.
   - **W2 Groups.** No group of glyphs a layout rule ties spans two files.
   - **W3 Shaping.** Every string of the v0.3 and v0.4 cases, split into runs by file as a browser
     splits it and shaped with HarfBuzz under each language, gives the whole TTF's advances and offsets.
   - **W4 Faces.** Weight ranges and styles are as locked; each chunk's overrides are its face's in
     `fallback.json`, computed as DirectWrite reports them.
   - **W5 Package.** Item 5's checks.
   *Done when:* it passes from a fresh clone, prints one line per check, and each mutation fails it: a
   code point moved to another chunk, a split kana group, a dropped range, an overlap, a weight range
   off by one, an override changed, a WOFF2 byte flipped, a stylesheet edited by hand.
7. **In Edge, to close.** On the measurement guest, the package's stylesheets served over HTTP from
   `build/npm-package/` (`probe/v0_6/browser.py`):
   - widths: every string of the v0.3 and v0.4 cases, in every Harena UI and J face, with no language
     and under `ko` and `ja`, at 1000 px, lays out in the package's family exactly as with the face's
     whole TTF. The TTFs against Segoe are v0.2–v0.4's batteries, already passed; this replaces
     rerunning them against the stylesheets, which the spec first said, since what the package can change
     is how a browser splits and finds the files, and that is what this compares;
   - line boxes: every J code point outside Harena UI, after `A`, at 14 and 40 px, in each J face, with
     no language and under `ko` and `ja`, against the Segoe stack's: equal with no language, the
     characters item 2 found drawn by another face aside, which are counted, as are those that differ
     under `ko` and `ja`;
   - fetches, from each page's resource list: Latin and icon text after Segoe fetches nothing; Latin in
     Harena UI alone fetches its face; Hangul after Segoe fetches KS X 1001's chunk, and a rare syllable
     the one other chunk that has it.
   *Done when:* all three hold, with the counts recorded here.

**Result** (2026-11-03).

- *Files.* 211 WOFF2, 31.6 MB in the package: fifteen Harena UI faces (49 KB each), the icons
  (156 KB), and thirteen chunks per J face, the largest 218 KB. Two builds write the same bytes, once
  each file keeps its TTF's timestamp. `j.css` is 81 KB, 2.4 KB under gzip.
- *Item 2.* With no language, Windows draws 594 of J's 19,390 code points outside Harena UI from
  another face than their chunk's (1,469 in Light, where Microsoft JhengHei UI and YaHei Light share
  Han). For every chunk and weight, J Text with its face's overrides gives Windows' line box at every
  size from 9 to 96 px for a line of up to 40 of the characters that face draws.
- *Gate.* `verify_web.py` passes, 16 checks; `mutate_web.py` catches all sixteen mutations.
- *In Edge* (Edge 151 on the guest, `probe/v0_6/browser.py`): 880,110 widths, every string of the
  v0.3 and v0.4 cases in all thirty faces under three languages at 1000 px, equal to the whole TTFs';
  1,745,100 line boxes, none different with no language beyond the characters item 2 counts (13,854
  measurements over fifteen faces and both sizes), and, counted, 25,086 under `ko` at 14 px, 80,850 at 40 px, and 117,066 under
  `ja` at each size, where Windows draws kana and Han from Malgun Gothic or Yu Gothic; and seven pages
  fetching exactly what was expected. A rare syllable fetches KS X 1001's chunk and then the one that
  has it, as CSS Fonts 4 resolves overlapping ranges.
- *Code review.* Codex, FIX-FIRST: package output could delete any directory under the repository;
  the gate crashed on an unknown weight range before W4 could report it; W3 shaped file runs alone
  on both sides, so it could not see a boundary effect; two mutations were caught for other reasons
  than their names, and the byte flip was missing; `index.css` was not checked; the measurement cache
  was reused without a fingerprint; the README still said Windows was unchanged. All fixed: output only
  under `build/`, W3 now shapes each script run whole against its pieces, the mutations split and
  overlap files for real, `index.css` is generated, the cache needs `--reuse` and a matching
  fingerprint. One mutation, a glyph shifted whole, was found to change nothing a renderer draws, since
  it places a glyph by its side bearing; it scales the glyph instead. Codex again, FIX-FIRST: W3 split
  hiragana from katakana, which Chromium shapes as one run, so a pair across them went unseen; the
  cache's fingerprint left out the guest and the probe, and an old cache crashed it; the package README
  promised Windows' line heights without the exceptions. All fixed: W3 itemizes by script extensions
  as Chromium does, with a mutation adding such a pair; the fingerprint takes the provenance and the
  probe's bytes. A third look found W3 still settled a run's script at its first character (`、あ`
  as Bopomofo, then kana) and the fingerprint without the fonts' hashes: W3 now narrows each run's
  scripts as its characters come, as Chromium does, with three such strings added since no case
  opens that way and a mutation pairing them; the fingerprint takes every face file's hash, and a
  cache of the wrong shape is ignored; the repository README states the line-height exceptions too.

**Out of scope, and where it goes**

- Publishing to npm and tagging a release: the owner's, after the close.
- Linux and macOS rendering, and matching for installed (not served) fonts: 1.0.
- Icons outside `Symbol`, Trim and Reshare: later, as v0.5 left them.
- Slicing by frequency: when a page shows it fetches more than it uses.
- Line boxes item 7 counts, under `ko` and `ja` or where Windows mixes faces: when a layout shows one.
- Windows' own Hangul by `local("Malgun Gothic")`: when a Korean page on Windows asks for it.

## v0.5 — Harena UI Icons, at Segoe Fluent Icons' geometry (closed 2026-11-02)

**Goal.** Every code point Segoe Fluent Icons maps draws in Harena UI Icons, a stand-in from open
outlines, with Segoe's advance, line box and ink box, so a stack naming it after Segoe lays out the
same in Edge.

**What Segoe Fluent Icons is** (explored 2026-11-01 on the measurement guest, Edge 151; item 1 commits
the data). Its SHA-256 is `866a2faa…edec`.

- **2,008 code points draw 1,609 distinct glyphs.** 2,005 are Private Use Area; the others are U+0000,
  U+000D and the space. No layout tables: no GSUB, GPOS or `kern`, and no hinting programs.
- **A static face is enough.** 2048 units per em; ascent 2048, descent 0, gap 0 in `hhea`, `typo` and
  `win`, and the line box is exactly 1 em at 12–40 px. `font-weight` 300–700 and `font-style: italic`
  change no width at 12–1000 px.
- **1,979 code points are 1 em wide; 26 icons and the space are not**, and two controls are 0. Fifteen are 1.5–2.6 ems.
  Those fifteen draw text, not pictures: IME key legends such as `、。?!`, `abc`, `＠ ％ ＃`.
- **Microsoft's published list names 1,467 of the 1,609 glyphs.** The other 142 include script legends
  (`字`, `가`, `G`) and long ladders of battery states. Names do not reach Fluent's: only 201 of 1,573
  match exactly, so a script cannot choose the stand-ins.
- **Segoe draws 69 named glyphs as mirrored forms**, 49 as `Solid` and 34 as `Fill`, parts meant to
  stack on another glyph among them.
- **Segoe MDL2 Assets is not the target.** It shares 1,832 points with Segoe Fluent Icons and has one
  more, and some widths differ there (U+F1D4 and U+E843 among those sampled). It precedes this font on Windows 10 only.

**Locked — one row per Segoe glyph, in a reviewed table.** `data/icons/table.json` has one row for each
of the 1,609 glyphs: its code points, Microsoft's name if published, and what draws it, one of:

| kind | draws | for |
|---|---|---|
| `fluent` | one Fluent UI System Icons SVG, a quarter turned where Segoe draws upright what Fluent draws on its side (battery ladders, 23 rows) | the same idea in Fluent's drawing |
| `compose` | a Fluent SVG and a filled Fluent badge, by one fixed recipe | states Fluent has no icon for, when the rules below pass |
| `mirror` | another row, flipped | Segoe's mirrored forms |
| `text` | Harena UI J outlines of the row's weight, or Pretendard JP's where J has none of the symbols (4 rows) | letters, script legends and IME key legends |
| `holes` | the cut-out subpaths of a filled Fluent SVG | symbols that stack on another glyph |
| `bars` | four rising bars, `level` of them filled and the rest outlined | Segoe's signal ladder, ZeroBars to FourBars (added after review) |
| `blank` | nothing | glyphs with no ink in Segoe |
| `none` | one neutral placeholder | no counterpart, counted |

*Rejected:* a name-matching script alone (201 of 1,573 exact). *Rejected:* one row per code point, which
would let two points Segoe draws alike draw differently. *Rejected:* drawing new outlines, or adjusting
a Fluent one toward Segoe: nothing here may be traced, and every outline is one upstream's, fitted whole.
*Amended* (owner's review, 2026-11-02): `bars` is the one exception, five rows of plain rectangles on a
20 grid, because no upstream draws a ladder with its empty bars. Its numbers are this file's own, chosen
for four rising bars, not measured from or traced over Segoe's; nothing else may be drawn new.

**Locked — Segoe's pictures are working input, never data.** Choosing needs Segoe's glyphs in view, as
winui-svelte's 229 rows did. Rendered sheets stay in `.private/` and are input only: they go to the
models choosing and reviewing and to the owner, and no pixel or trace reaches a tracked file. What is
committed from Segoe is what the other families commit: code points, advances, ink boxes, metrics and
Microsoft's published names.

**Locked — open sources, Fluent first.** Outlines come from Fluent UI System Icons (Microsoft, MIT). A
row may take another source only if Fluent and every kind above fail it, the source is one Microsoft's or
an MIT or Apache-2.0 set whose outlines state their origin, and the row says so; which sources is decided
from what remains after item 2's first pass. SymbolIconManager's `SegoeFluent.json` (MIT) supplies
candidates, never outlines: it names a Fluent icon for 625 of the 1,609 glyphs, and agrees with
winui-svelte's rows on 164 of the 192 where both name one.
*Rejected:* Uno Fluent Icons' outlines, the widest coverage (1,192 glyphs), because some are stated to be
unique to it and nothing says how they were drawn. *Rejected:* a general set such as Material Symbols as an
equal source: no mapping, another style.

**Locked — models choose, code draws, and a composition has to earn its place.** A pass over Fluent's own
composites (368 pairs, 2026-11-01) found one recipe near Fluent's drawing for 47% of them, and shows why:
Fluent's designers move the badge or redraw the base, and a fixed recipe cannot. `call_warning` loses the
phone. No single number separates good from bad, so:

1. No model produces an outline. A model picks from existing rows; code makes every shape.
2. A native Fluent composite is taken whenever one exists.
3. Otherwise one recipe only: a filled badge at the bottom right, with the base knocked out around it. An
   outlined badge is unreadable at 16 px.
4. A composition removing 40% or more of its base's ink fails, automatically. 40% is provisional, from that pass.
5. Compositions pass by family, one sheet at real size (16 and 20 px), by the owner.
6. What fails is never forced: it takes its base alone, marked near, or `none`.

**Locked — fitted without distortion.** Each outline is scaled uniformly until it fills the Segoe ink box
on one axis, and centred on the other. Stroke weight follows from the fit and is not matched: it is shape,
not layout. Fluent size is 16 first, then 20, then 24; a composition's base is on the recipe's 20-unit grid.
`Solid`, `Fill` and `Bold` rows take `filled`; others take whichever drawing inks nearer Segoe's glyph.
*Rejected:* choosing by cosine, which picked filled twice as often: normalising favours a solid shape.

**Locked — coverage is Segoe Fluent Icons' map, nothing more.** The one MDL2-only point and U+F5F0 stay out.
WinUI's `Symbol.Target` names U+F5F0, but neither font of its `SymbolThemeFontFamily` maps it; of 254 font
files scanned on the guest only fonts private to apps do, and Edge draws a missing-glyph box. winui-svelte's
own face behind this one still draws it.

**Licence.** Font under OFL 1.1, as the others. Fluent's outlines are MIT, whose notice ships beside the
font (`docs/LICENSE-Fluent-UI-System-Icons.txt`). Text rows carry Open Sans's and Pretendard JP's outlines, so
the font's copyright string names them, with Pretendard JP's Reserved Font Name; no Harena name contains it.
OFL's text is not yet in the repository, and Harena UI J's string omits the reservation wording: v0.6, with delivery. Sources are pinned by SHA-256:
`@fluentui/svg-icons` 1.1.345 and SymbolIconManager's mapping file at a commit.

**Items**

1. **Measure.** `probe/v0_5/`, writing `data/v0_5/segoe-icons.json`: every code point, its advance, its
   ink box and its glyph group, with the font's SHA, in numbers only.
   *Done when:* 2,008 code points in 1,609 groups, and DOM width at 1000 px equals each advance, the two controls aside.
2. **The table.** In this order, so that a model sees only what code cannot settle:
   - Code settles `blank`, `mirror` and `text` rows. It proposes without a pick any row where SymbolIconManager
     and raster similarity agree. Similarity is computed in the guest, and only rankings leave it.
   - winui-svelte's 229 rows are carried over, re-checked against item 1's boxes.
   - A cheap model picks the rest on sheets of ten rows, Segoe beside eight candidates, twice over. Rows it marks
     as having no match, or on which its two runs differ, go to a stronger model. In a pilot of 60 against
     winui-svelte's rows, Haiku chose the row's icon in 42 of the 45 where it was offered, and Sonnet 39.
   - The pilot's weakness was candidates, missing from 15 of 60, so a text pass over Fluent's names widens them
     (`HangUp` to `call_end`) before any sheet is drawn.
   - Every row is then reviewed by another vendor's model on an overlay sheet, and the owner gets the whole set
     in a local page in `.private/`.

   *Done when:* every glyph has one row, the second model's objections are settled, the owner has passed the
   sheets and the composition families, and the `none` count is recorded here with what each `none` is.
3. **Build and gate.** `scripts/build_icons.py` (fontTools; reproducible), and checks in `verify.py`, which
   fail unless:
   - the `cmap` is exactly Segoe's 2,008 points, and each row's points share one glyph;
   - each advance equals Segoe's in font units;
   - metrics are 2048/0/0 in all three places; there is no GSUB, GPOS, `kern`, hinting or colour table;
   - each row's ink lies within Segoe's box within 2 units (outlines round), fills it on one axis and is centred
     on the other; `blank` rows are exactly those with no ink in Segoe; the 4 `holes` rows are excluded, and
     must sit inside their circle's box, where Fluent placed them, so they align with it;
   - each outline is reproduced from its row and its source file: a font with any other outline fails. This
     cannot catch a bug in the build's own SVG reading, so item 4 compares every glyph with its SVG as Edge
     parses it;
   - `none` is exactly the recorded count, each Fluent name exists in the pinned package, and each `compose` row
     removes under 40% of its base's ink;
   - two builds are byte-identical, and `SHA256SUMS-Icons` matches.
   *Done when:* a fresh clone's gate passes, and each mutation in `scripts/mutate_icons.py` fails its own check.
4. **In Edge.** `probe/v0_5/`: under `"Harena UI Icons"` alone, against `"Segoe Fluent Icons"`, every code
   point at 12–40 px and 1000 px, across weights 300–700 and italic, in DOM and canvas; line box height at each
   size; strings of mixed icons and text under the stack; and that the stack draws Segoe's pixels where Segoe is
   installed.
   *Done when:* every width is within one layout unit and every line box equal, with no exclusions, or any
   exclusion is named and counted here.

**Result** (2026-11-02). All four items are done; item 2 closed on the owner's pass of the rows WinUI's `Symbol`
draws, below, and the other rows' remaining faults are later work.

- *Table.* 1,609 rows: 1,337 `fluent` (174 marked near, the general idea rather than the same picture), 119
  `compose`, 91 `text`, 44 `mirror`, 5 `bars`, 4 `holes`, 3 `blank` and 6 `none`: E4E8, E614, Wheel (EE94),
  TrafficLight (EF31), Ear (F270), HearingAid (F27F). Fluent has no counterpart for these.
- *How rows were settled.* Codex reviewed every row on overlay sheets; of its 268 findings 217 said WRONG. The 97
  changes it named were taken (`probe/v0_5/review_fixes.json`), though the battery ladder overrides 11 of them.
- *The second review, for meaning.* The owner saw stand-ins that could change what an icon means, so the rows were
  judged again: Sonnet on every sheet, joined with what Codex's first round had left open, 325 rows. Sonnet chose
  again for each, widening the badge recipe to any filled Fluent stem where the original is an object plus a state,
  and Codex judged the 199 rows that changed. It rejected 65, which keep their earlier choice, as does one more whose
  combining mark the build cannot place. Three badges gave way to Fluent's own drawing: E670, E809, EC75.
- *WinUI's `Symbol` first* (owner, 2026-11-02). The owner set the bar for v0.5 at the 193 rows WinUI's `Symbol` enum
  draws (`SymbolIcon`; its 197 members as winui-svelte records them from WinUI's source, `Target` aside), and moved
  the rest to later work. All map and none is a placeholder. Codex judged them on their own sheets twice; 16 changed
  between the runs, as an object plus its state where Fluent has no single drawing. The second run still lists 25,
  mostly a missing mark (signal bars drawn without their empty bars, Trim as scissors); its calls differ between
  runs on the same drawing, so these go to the owner rather than another round. The owner's read: the four signal
  levels must show their empty bars, as Segoe does, and Preview must not draw what Scan draws. Fluent draws
  neither empty bars nor a page preview, so ZeroBars to FourBars are a fifth recipe, `bars`: four rising bars on a
  20 grid, as many filled as the level and the rest outlined; Preview is a page with an eye badge.
- *Owner's pass* (2026-11-02): the 193 `Symbol` rows pass. Trim (scissors, which read as Cut) and Reshare (the
  same drawing as Share) pass for now; a picture of shortening and one Reshare can be told from Share by are later
  work.
- *Later.* Outside `Symbol`, those 66 rows, and the 85 of the 325 for which nothing better was found, can still lose a state or
  read as something else: print-layout diagrams, staples, SIM and VPN marks, gestures. A later reader should not
  take the Edge results below as saying anything about meaning; only the owner's pass does.
- *In Edge.* 168,504 widths at seven sizes and six styles are all within one layout unit, with no exclusion but
  the two controls that cannot be laid out alone. Line boxes are equal at every size; 28 strings of text and icons
  under a stack match in width and height; the stack draws Segoe's pixels at every point. All 1,606 inked glyphs,
  of every kind, match what Edge draws from their sources, E7A5 aside: its Segoe box is a sliver, too small to
  compare. Each kind fails against another kind's drawing and with its recipe undone. Synthetic bold was last
  measured before the second review.
- *Code review.* Codex's quota ran out before the first: a new Opus context reviewed the branch, FIX-FIRST on the
  copyright string and six gate and record gaps, all fixed. When it returned, Codex reviewed the branch, FIX-FIRST on
  a style fix a seeded icon ignored, a comparison that left out 218 rows, and a hinting check that read only table
  names, all fixed.

**Out of scope.** WOFF2, npm and the stylesheet: v0.6. Linux and macOS rendering: 1.0. Matching stroke weights,
colour icons and Segoe MDL2 Assets' widths. winui-svelte changing its stack, which is its own decision.

## v0.4 — Harena UI J, at the widths Windows gives CJK (closed 2026-10-31)

**Goal.** In all fifteen faces, Harena UI J lays out Hangul, kana and Han at the widths Edge gives
them under a Segoe stack, for each language a page can set, with its Latin identical to Harena UI.

**What Windows does with CJK** (explored 2026-10-31 on the measurement guest, Edge 151, in DOM at
1000 px; item 1 measures every face and commits the data):

- **Nearly every character is 1 em.** All 11,172 Hangul, all kana and all but a few Han, in every
  face, whichever font draws them. Halfwidth forms are 0.5 em. Hangul pairs and Han pairs show no kerning (40 of each
  sampled against each other).
- **The font that draws a character depends on `lang`.**

  | `lang` | Hangul | kana | Han |
  |---|---|---|---|
  | none, `en` | Malgun Gothic | Yu Gothic | Microsoft YaHei |
  | `ko` | Malgun Gothic | Malgun Gothic | Malgun Gothic |
  | `ja` | Malgun Gothic | Yu Gothic | Yu Gothic |

  `zh`, `zh-Hans` and `zh-Hant` give the widths `ja` gives alone, apart from a few characters in Bold,
  and no trimming or kerning. `de`, `vi`, `ru`, `ar`, `th` and `hi` give what no `lang` gives, and so
  does winui-svelte's whole stack (`"Segoe UI Variable Text", "Segoe UI", sans-serif`).

- **Widths depend on the neighbours as well, because a run of one script draws in one font.** Chromium
  splits text into script runs, and punctuation joins the run beside it.
  - In a Hangul run with no `lang`, the same 12 brackets are Malgun's, though alone they are 1 em:
    `가「` and `「가` are about 1.57 em. This is winui-svelte's gallery, which sets `lang="en"`.
  - In kana under no `lang` and `ja`, Yu Gothic's kerning applies: 2,798 of 30,976 kana pairs and 333
    kana-and-punctuation pairs, up to −200 px at 1000 px. `ア、` is 1.86 em. No pair across Hiragana and
    Katakana kerns, though Chromium shapes both as one run.
  - Under `ko` and `zh` none of this kerning appears.
- **So widths depend on `lang` in three more places.**
  - Under `ko`, 12–14 brackets (`〈〉《》「」『』` and others) are Malgun's, 0.52–0.60 em.
  - Under `ja`, Edge's `text-spacing-trim` (on by default) closes up adjacent full-width punctuation
    through Yu Gothic's `halt`: `」「` and `、。` are 1.5 em, not 2.
  - In Semibold and Bold, Han and symbols the expected font lacks come from MS PGothic or SimSun at
    1.0195 em: 160 characters with no `lang`, 1,309 under `ko`, 56 under `ja`. Under `ja`, 82
    characters are 1 em that differ otherwise.
- **The line box grows with the fallback font.** winui-svelte's type ramp uses `line-height: normal`,
  so this reaches real layouts.

  | size | Latin | Hangul | kana (no `lang`, `ja`) | kana (`ko`) |
  |---|---|---|---|---|
  | 12 px | 16 | 16 | 20 | 16 |
  | 14 px | 19 | 19 | 22 | 19 |
  | 16 px | 21 | 21 | 26 | 21 |
  | 20 px | 27 | 27 | 32 | 27 |
  | 28 px | 37 | 37 | 45 | 37 |
  | 40 px | 53 | 54 | 64 | 54 |

- **Explicit East Asian requests change Windows' widths.** `palt`, `pwid`, `halt`, `hwid`, `twid`,
  `vert`, `ruby` and `font-variant-east-asian: proportional-width | ruby` all do, per font. No file in
  winui-svelte requests any of them, or sets `writing-mode` or `text-spacing-trim`.

**Locked — the CJK half is added to Harena UI's faces, not built beside them.** Each of the fifteen J
faces is that Harena UI face plus CJK glyphs. Its Latin is not rebuilt, so it cannot drift: the gate
requires it identical. Fifteen faces, named `Harena UI J Small` and so on, as ADR 0004. The CJK outlines
repeat across sizes.
*Rejected:* a J family of fewer faces. The superset would then not match Harena UI's Latin.

**Locked — coverage is Harena UI's plus Pretendard JP's CJK blocks.** Radicals, CJK punctuation, kana,
Hangul compatibility jamo, enclosed and compatibility forms, Han, compatibility Han, halfwidth and
fullwidth forms. Only code points Segoe does not map, since Segoe draws the rest on Windows.
Pretendard JP's Latin extensions, symbols and Private Use Area are not taken: those would be Inter
shapes among Open Sans', and Private Use Area code points mean different things in different
fonts (the Locked note on the icon family).
*Rejected:* taking everything Pretendard JP maps.

**Locked — a run's widths are positioning, not glyph copies.** The default advance is the width with
no `lang`. A character another script run or language gives another width takes a GPOS adjustment under
that script and language system, in `dist`, which HarfBuzz always applies: the brackets in `hang`'s
default system and in every script's `KOR`, the few that differ in `ZHS` and `ZHT`. Yu Gothic's kana
kerning is `kern` under `kana`'s default and `JAN` systems. Under `KOR` and `ZHS` only what is measured
there is, the few pairs of a character those fonts lack that narrow. Each new
script system also carries Harena UI's default features, so Latin punctuation in a CJK run keeps its
kerning. Under `JAN`, and in `kana`'s default system since Yu Gothic draws those runs too, `halt`
carries Yu Gothic's half-width punctuation, which is what Edge's `text-spacing-trim` reads. Both
were checked in Edge on the guest with a test face: `dist` under `KOR` narrowed `「」` under `ko` alone,
alone and beside Hangul, kana and Han; `halt` under `JAN` gave `」「`, `。」`, `（「` and `、。` 1.5 em under
`ja` alone, and left `「」` at 2 em and a sentence at its own width, as Yu Gothic does.
*Rejected:* one width per character, which leaves `lang="ko"` brackets nearly twice Windows' width.
*Rejected:* copies under `locl`. They add thousands of glyphs for what one adjustment does.
*Known cost:* `font-feature-settings: 'dist' 0` undoes the language's widths. Nothing requests it.

**Locked — where the run's first character picks an odd font, Windows is not matched.** A font cannot
tell which font Windows' fallback would have reached for. So these stay different, and the gate counts
them rather than passing over them: runs of only symbols whose first character's font draws the rest
(`㎀「`), or that start a run before Hangul or kana (`（「가`), and a symbol before a letter that it pulls into
its font in Semibold and Bold; U+30FB beside punctuation outside Japanese, which Yu Gothic draws and
trims; U+FF5F and
U+FF60 alone (0.5 em, 1 em beside anything), which take their width beside a letter; U+FA2E and U+FA2F
before Han, which keep their width alone (0.645 em); and U+3099 and U+309A alone, after anything but
kana, and under Chinese in Semibold and Bold; and a symbol beside a kana the language's font lacks,
which that kana's font draws wider (`ゔ｟` under `ko`). With no language, two more that Edge showed:
U+FF5F and U+FF60 beside one of ten symbols after Hangul (`가〖｟`, 1 em in the symbol's font, 0.5 em here),
which like `ゔ｟` a contextual adjustment could correct, but nothing writes these characters there; and
`）・` after a bracket around other letters after kana, and punctuation that starts a kana run where
Windows trims it anyway (`）（ア`, 0.5 em wider here). And in Semibold and Bold at 20 px and below, a
character Windows emboldens itself (160 symbols with no language, 1,309 characters under `ko`) takes a
whole pixel, up to 1 px per character more than here: a static width cannot vary by size, so it stays the
width from 28 px up. The trigger to reopen is a layout that shows one.

**Locked — with no language, `halt` needs kana before it.** A kana run can start at punctuation: Chromium
gives a closing bracket its opening bracket's script, so in `ファイル（F）、` the run is `）、`, and Windows'
fallback takes a font there that does not trim. So kana's default system applies `halt` only after kana,
past combining marks, with up to two punctuation marks between. Over 6,812 such texts measured on Text Regular this leaves 820
different where 1,893 were, and the menu label matches. *Rejected:* `halt` everywhere, 0.5 em short on that
label; no `halt`, which loses `ア）、`. Under `ja` Yu Gothic trims regardless, and `JAN` keeps it unconditional.

**Locked — explicit East Asian features are not matched in v0.4, and are removed.** A page that asks
for `palt`, `vert`, `ruby` or the like gets 1 em widths, where Windows gives each font's own. Matching
them means carrying three fonts' per-glyph values for requests no consumer makes. *This narrows what
v0.3's out-of-scope list sent here.* Vertical writing goes the same way: no `vert`, `vmtx` or `vhea`.
The trigger to reopen is a consumer that needs one.

**Locked — vertical metrics stay Segoe's.** One file has one set. With them, Latin and Hangul line
boxes are Windows' at every size measured to 28 px, and Hangul's is 1 px short at 40 px. Japanese lines stay short:
a kana line is 3 px short at 14 px and 8 px at 28 px, and Han under `ja` likewise. v0.6 can address that
on the web, where a kana or Han chunk can declare its own metrics by `@font-face`; it is recorded there,
not solved here.
*Rejected:* Malgun's metrics, which would move Latin in a J-only stack. *Rejected:* Yu Gothic's, which
would make every Korean and Latin line 20% taller.

**Locked — shapes as ADR 0003, verified here.** All advances as measured. Hangul is scaled uniformly by
about 1.08 to Malgun Gothic's body, with stem growth compensated through `wght`. Kana and Han keep their
size and gain space. Weights are matched by stem per face weight: Malgun Gothic's `ㅣ` for Hangul, Yu
Gothic's `十` for kana and Han. ADR 0003 left the scale and weight mapping to be verified on a built font.

**In scope**

1. **Measurement, committed.** As `data/v0_4/`, for each of the fifteen Segoe faces, under no `lang`,
   `ko`, `ja`, `zh-Hans` and `zh-Hant`, in DOM at 1000 px, with `en` for code points and fixed text
   alone, which must equal no `lang`:
   - every covered CJK code point's width, and which code points differ between languages;
   - every character covered that has no script of its own (Common, Inherited) and so joins the run
     beside it, before and after Hangul and Han;
   - every ordered pair of kana, and of kana with those symbols, on the Text faces; the kana pairs
     alone on Small and Display, which must equal Text's;
   - `halt`: every ordered pair of the full-width punctuation covered, with and without
     `text-spacing-trim: space-all`;
   - fixed sentences mixing Hangul, kana, Han, Latin, digits and spaces, and NFD Hangul and kana with
     U+3099 and U+309A, to confirm that widths add up and sequences compose;
   - line box heights at 12, 14, 16, 20, 28, 40 and 68 px;
   - stems (`ㅣ`, `十`) and ink bodies from pixels for each Windows face reached (Malgun Gothic Semilight,
     Regular and Bold; Yu Gothic Light, Regular and Bold; the Pretendard JP weights compared). Numbers
     only: the Segoe rule covers these fonts too.

   The scripts are committed.
2. **Build.** `scripts/build_j.py` takes each built Harena UI face and adds CJK:
   - instances Pretendard JP at the stem-matched weights, separately for Hangul and for kana and Han;
   - scales Hangul, sets every advance, and keeps each glyph's source balance in it. Opening
     punctuation keeps its trailing bearing and closing punctuation its leading one, because `halt`
     and a narrower width cut the empty side;
   - adds `dist` and `halt` under their language systems, and the script and language systems they
     need;
   - keeps Harena UI's features and adds no others;
   - rebuilds `name` as Harena UI J, with no reserved name; declares the CJK blocks and code pages in
     `OS/2` (Harena Term's ADR 0012).
3. **Gate.** `scripts/verify.py` runs these over the J faces, alongside checks 1–12 on Harena UI:
   - **13 Latin identity.** Every v0.3 case and base+mark pair shapes to the same glyphs and positions
     in the J face and its Harena UI face, and vertical metrics, outlines and advances of Harena UI's
     glyphs are equal.
   - **14 Coverage.** The cmap is exactly Harena UI's plus the code points the Locked note lists.
   - **15 CJK widths.** Every code point, neighbour, pair, sentence and sequence of item 1, under its
     language and script, shaped with HarfBuzz, within half a unit of Windows'. A trimmed pair is shaped
     with `halt` on the character Edge applies it to, since HarfBuzz does not trim by itself. What the
     Locked note leaves different is left out and printed as a count.
   - **16 Features.** GSUB and GPOS features are exactly Harena UI's plus `dist` and `halt`; `dist`,
     `halt` and the kana `kern` are empty outside their language systems; `halt` only halves what the
     measurements show.
   - **17 Shapes.** Stems within 3% of the target per face weight; Hangul's median ink body within 2% of
     Malgun Gothic's; every outline equal to Pretendard JP's at the chosen weight, moved and, for Hangul,
     scaled only.
   - **18 Reproducible.** Two builds are identical, as check 8.

   The gate is shown failing first for: a Latin glyph changed in a J face; a CJK advance off by a unit;
   a `dist` adjustment under the wrong language; the whole kana `kern` under `KOR`; a `halt` pair too many; an added code point; an orphan
   glyph; a Hangul outline at the wrong scale.
4. **In the browser, once, to close.** Each J face against its Segoe face in Edge, in DOM, per language.
   At 1000 px: all of item 1's cases, and each punctuation pair after Hangul, Han and kana. At 12, 14,
   16, 20 and 28 px: the same but for kana pairs that do not kern and pairs after a letter, with every
   20th Hangul and Han, since those advances scale with size and the 1000 px run has them all; all
   kana pairs on Text at 14 px. Line heights are reported apart, not judged. Tolerances are v0.2's.
   Harena UI's checks are rerun. The font bytes loaded are checked in the page.

**Out of scope, and where it goes**

- Han and halfwidth katakana Pretendard JP lacks: they fall through the stack, as Harena Term's D4
  accepted for Han.
- Explicit East Asian features and vertical writing: when a consumer needs them.
- Japanese line heights, and Hangul's 1 px at 40 px and up: v0.6.
- A Korean-form Han cut: when evidence asks, as already locked.
- Shapes on Linux and macOS rasterizers: 1.0.

**Done-when.**
- `python scripts/verify.py` passes checks 1–18 on all faces. It exits non-zero on any failure, and on
  any mutation under item 3.
- On the guest, item 4 passes within v0.2's tolerances.

**Review.**
- Three units: measurement; build and gate together; browser check. Each is reviewed in a separate
  context before sealing.
- The milestone closes with a reproduction from a fresh clone and a cross-model adversarial review.

## v0.3 — every feature a browser can request, at Segoe's widths (closed 2026-10-31)

**Goal.** In all fifteen faces, every OpenType feature and language a page can request through
CSS lays out at the width the Segoe UI Variable face gives for the same request. Features Segoe
has are matched; features it lacks are removed.

**What Segoe does with features** (explored 2026-10-30 on the reference guest, Edge 151, Text
Regular only, in DOM at 1000 px; item 1 measures every face and commits the data):

- **Segoe has few features.** GSUB has `ccmp`, `dlig`, `frac` and `tnum`. GPOS has `abvm`,
  `kern`, `mark` and `mkmk`. The one language system is `latn`/`TRK`, and `lang="tr"` changes no
  width. Segoe has no `liga`, `locl`, `pnum`, `onum`, `lnum`, `zero`, `ordn`, `sups`, `subs`,
  `numr`, `dnom`, `salt` or stylistic sets. Requesting any of them leaves Segoe's widths
  unchanged. These tags were read on the guest, like v0.1's cmap; only tag names left it.
- **Harena UI keeps Open Sans' features, so the same requests change its widths.** Measured on one
  test line: `pnum` +63 px, `ss01` +92 px, `ss04` −139 px, `sups` −1,599 px, `lang="ca"` −144 px.
  `lang="mh"`, `nv`, `sr` and `mk` also change widths, as does `font-variant-position: super`.
  None of these change Segoe's.
- **Segoe's `dlig` changes widths, and Harena UI has no `dlig`.** With
  `discretionary-ligatures`, Segoe's `ff`, `rf` and `rt` get 3–4 px narrower, and `ffi` and `ffl`
  get 21 px wider.
- **Segoe's `frac` has widths of its own.** `1/2` under `diagonal-fractions` is 890 px in
  Segoe and 856 px in Harena UI. The same gap shows with no CSS feature in `1⁄2` (U+2044),
  because HarfBuzz applies `frac` around a fraction slash by default.
- **`ccmp` differs in one place among the marks Harena UI maps.** Cyrillic `і` and `ј`
  followed by a mark are 2.5 and 2.9 px wider in Harena UI: Open Sans' `ccmp` swaps in a
  dotless glyph whose advance is different. Segoe's widths do not change.
- **The other mark differences come from coverage.** Open Sans maps 18 of the 112 combining marks
  in U+0300–036F, and Segoe maps nearly all of them. A sequence with an unmapped mark falls back
  to another font. Segoe also composes `a` + U+0307 into `ȧ` (U+0227) and `R` + U+030F into `Ȑ`,
  and Open Sans has neither precomposed letter. Both cases stay out of scope with v0.2's
  coverage note.
- **Already equal:** synthesized small caps (all five `font-variant-caps` values),
  `font-kerning: none`, explicit `tnum`, `liga` on or off, `ccmp` off.

**Locked — a feature stays only if Segoe has it.**
- Every feature Segoe lacks is removed from every face, in every language system. So are the
  glyphs that only those features reach.
- Windows shows Segoe without these features. Open Sans' versions change shapes as well as
  widths: oldstyle figures, a one-storey `g`, Catalan `l·l`, Romanian comma accents.
- The one exception is `liga`, kept from v0.1. Its ligatures already take Segoe's widths for the
  same letters, and the gate checks that (check 2).
- *Rejected:* keeping the alternates and forcing each to its default glyph's width. The layout
  would match, but a page would show shapes Windows never draws for that request. Every kept
  alternate would also need a width copy and a gate rule.

**Locked — `dlig` is Segoe's substitution, onto Open Sans' own glyphs.** *Changed after the
milestone review;* the first version matched `dlig` by GPOS positioning, rejected below.
- Segoe's `dlig` ligatures are its presentation forms. `ff`, `ffi`, `ffl` and `ﬀi` under
  `dlig` are as wide as U+FB00, U+FB03 and U+FB04 to within 0.012 px in every face measured, and
  kern against their neighbours as those characters do in 548–551 of 552 measured contexts.
  Its contextual `r` before `f`, `t` and their kin is a glyph of its own width, unkerned against
  the printable ASCII around it.
- Harena UI's `dlig` substitutes the same way. Segoe's sequences become the presentation form
  that decomposes to them (Open Sans' own `ﬀ`, `ﬃ`, `ﬄ`, whose widths and kerning are already
  Segoe's from v0.2), from letters and from a default ligature alike. `r` before Segoe's
  lookahead characters becomes `r.dlig`, a copy of Open Sans' `r` with Segoe's advance, measured
  with kerning off. Kerning against these glyphs is in `kern`, so `font-kerning: none` and
  `liga` off combine with `dlig` as in Segoe.
- Segoe's `ccmp` draws `i` and `j` dotless before a spacing accent (`` ` `` `¨` `´` `ˆ` and ten
  more, read from v0.2's measurements, where `i` before them measures as `ı`, and confirmed with
  kerning off), so its `ffi` does not form there. Harena UI's `ccmp` does the same (item 2), so
  `liga` and `dlig` meet a dotless `i` there too.
- *Rejected:* GPOS positioning on the default glyphs (the first version). Its corrections for
  the neighbours' kerning sat under `dlig`, so they stayed on with kerning off and were missed
  with `liga` off. Anchored to measured runs, they missed contexts no text measured (`Trfi`,
  where `liga` forms `fi`) and characters no context held (`off…`), and a positioning layer
  admits rules that cancel on every measured text and not elsewhere (the Codex review showed a
  defective face passing the gate). *Rejected:* drawing `r_f` and `r_t` ligatures, which would
  be outlines that are not Open Sans'.

**Locked — `frac` and `ccmp` stay, at Segoe's widths.**
- Open Sans' `frac` forms numerators, denominators and the fraction slash itself, so it does not
  need the `numr` and `dnom` features, which are removed. The glyphs it outputs take Segoe's
  `frac` widths, measured per digit as numerator and as denominator.
- `ccmp` keeps Open Sans' substitutions, which put marks on the right glyph. A substitution
  whose output's width differs from what Segoe gives for the same sequence points at a copy
  with Segoe's width. That copy is made the way `.liga` copies are; today it is needed only for
  Cyrillic `і` and `ј`. *Changed while building:* the width is the one Segoe gives the letter
  and mark (item 1's matrix), not the letter's own. Segoe draws `i` + U+0307 as wide as its
  dotless `ı`, which in Small and Display Light differs from `i`, and Cyrillic `і` + a mark as
  wide as `і`. An output only `ccmp` reaches (the four dotless forms of `і`, `ј`, `į`, `ị`)
  is respaced in place, and a copy is made only for an output that is also a mapped glyph and
  needs another width: today U+FB4A, Hebrew `ת` with dagesh (item 2).

**In scope**

1. **Measurement, committed.** On the reference guest, for every face, as `data/v0_3/`:
   - Segoe's GSUB and GPOS feature tags and language systems. These are read on the guest, and
     only the tags leave it.
   - Every input sequence of Segoe's `dlig` and `frac`, enumerated on the guest from Segoe's
     GSUB coverage, as code-point strings only. Each one's DOM width at 1000 px, with and
     without the feature. *Tightened after the milestone review:* the first export also carried
     lookup indices, types and flags; now only tags and code points leave the guest, and what
     the probe relies on (no flags, feature variations or required features; the forms read)
     is asserted there. `dlig` and fractions are also measured with kerning off, and `dlig`
     with the default ligatures off; the feature matrix adds every combination of two or more
     of `dlig`, `frac`, `tnum`, kerning off and `liga` off.
   - Fractions, with `/` and with U+2044, under `diagonal-fractions` and without it. Every
     digit is measured as a numerator and as a denominator.
   - A base-and-mark matrix: every target letter followed by each combining mark Harena UI
     maps, with and without `lang="tr"`. *Widened after the milestone review* from U+0300–036F
     to every mark both fonts map, adding U+0483–0489 and U+05BC. A mark of the inherited script
     is compared after every letter; another, after the letters of the scripts it is used with
     (Unicode Script_Extensions): a Hebrew point after a Latin letter is not text. `i`, `j`,
     `į`, `і`, `ј`, `ị`, `fi` and `ffi` are also measured before every spacing accent, with and
     without `dlig`, kerning and `ccmp`; and every pair Segoe kerns, with `ccmp` off.
     Every ligature Open Sans' `ccmp` or `liga` forms, and each Segoe `dlig` sequence and
     context, is measured with ZWJ in each subset of its gaps: a joiner keeps composition from
     hiding a rule from plain text (`A`, ZWJ, ogonek reaches the rule `Ą` hides). The same rules are
     measured with CGJ, and each letter alone and before CGJ.
   - A feature matrix on fixed lines covering:
     - every GSUB and GPOS tag in either font, set through `font-feature-settings`;
     - every `font-variant-*` value;
     - every language either font has a system for;
     - `font-kerning: none`.

   The scripts that do this are committed, as v0.2's were.
2. **Build.** `scripts/build.py`:
   - removes the features Segoe lacks, and the glyphs they alone reach;
   - adds Segoe's `dlig` as a substitution (the Locked note above);
   - sets `frac`'s glyphs to Segoe's widths;
   - gives `ccmp`'s outputs Segoe's widths, at copies where needed.

   Everything else is v0.2's build, unchanged. Coverage does not change: no code point is added
   or removed.

   *Found while building:*
   - **Kerning inside a ligature moves into `kern`.** A default ligature's advance is now the
     sum of its letters' advances. The kerning between them is a single adjustment on the
     ligature glyph, in the `kern` feature. With kerning on, its width is v0.1's: Segoe's for
     the same letters. With `font-kerning: none` it is Segoe's unkerned width, which v0.2's
     advance missed by the inner kerning (32 units on the test line in Text Light). The
     ligatures' ink moves with their changed advance, by the sidebearing split.
   - **Marks, after the milestone review.** The widened matrix found three things, each now
     matched from it:
     - U+0488 and U+0489, Cyrillic signs both fonts space, take Segoe's width;
     - a `ccmp` ligature of a letter and a mark takes Segoe's width for them: Open Sans joins
       Hebrew `ת` and dagesh into U+FB4A, as wide as `ת` in Segoe (a copy, `uniFB4A.ccmp`);
     - Segoe draws `i`, `j` and `ị` dotless before the Cyrillic pneumata U+0485 and U+0486 too,
       and `i` and `j` before the spacing accents, with kerning on or off. Both join the
       lookahead of Open Sans' own dotless rule, which covers `į`, `і`, `ј` and `ị` as well;
       Segoe was measured for `i`, `j` and (with the marks) `ị`. v0.2's kerning had stood in
       for the accents, which held only with kerning on. Those pairs are gone: with `ccmp`
       off, Segoe sets `i` and `j` before the accents unkerned (measured), so Harena UI does
       not kern a letter its `ccmp` makes dotless against them (the second milestone review
       found the pair still applying under `'ccmp' 0`). To rule out any other v0.2 pair standing
       in for Segoe's `ccmp`, every pair Segoe kerns in any face is also measured with `ccmp`
       off; all match.
   - **`ccmp`'s other ligatures, after the seventh milestone review.** Each takes the width Segoe
     gives its characters, measured with ZWJ between them. Open Sans' `ι` and `υ` with three marks
     were 119 and 63 units too wide in Text Regular, respaced in place since only `ccmp` reaches
     them. `Ǫ` and `ǫ` before spacing `ˉ` are as wide as both characters in Segoe, so `Ǭ` and `ǭ`
     get copies (`uni01EC.ccmp`, `uni01ED.ccmp`).
3. **Gate.**
   - Check 9 (tables) learns the new known differences:
     - the removed features and glyphs, against an Open Sans reference stripped the same way by
       the gate's own code;
     - `kern` as one or two lookups (pairs, then ligatures' inner kerning) after Open Sans' own;
     - the `dlig` lookups, appended after Open Sans' GSUB lookups and reached by nothing else;
     - exactly the characters Segoe draws `i` dotless before (marks and spacing accents), added
       to Open Sans' dotless rule; the gate derives them from the measurements itself;
     - `frac`'s and `ccmp`'s glyph widths, which check 12 holds;
     - the `ccmp` copies; and `tnum`'s copies, only for digits (the sixth milestone review
       found a non-digit's copy passing on build.json's word).
   - It also gains two checks:
     - **11 Features.** Each face's GSUB features are exactly `ccmp`, `dlig`, `liga`, `frac`
       and `tnum`, and its GPOS features are exactly `kern`, `mark` and `mkmk`. This holds in
       every script and language system, and each feature does the same in every one: every
       feature but `ccmp` resolves to the same lookups in every language system of every
       script, and `ccmp` (which Open Sans varies by script) to the same lookups across a
       script's language systems. No language then has a feature of its own, as none of
       Segoe's does, so a language combined with a feature lays out as the feature alone
       (the fourth milestone review found an empty `tnum` for Catalan passing, and the fifth
       one listed before the real one; a language system now lists each feature once). Every glyph
       is reachable from the cmap through those features. `dlig` is Segoe's, rule by rule: a ligature reads characters that join (after
       NFKC) into a Segoe sequence and puts out its presentation form; a single substitution
       turns a default ligature of such a sequence into that form; a contextual rule turns a
       character of a Segoe context, before glyphs that begin with a character that may follow
       it, into its `.dlig` copy. Each Segoe sequence shapes to its form with `liga` on and
       off. Outside them no character, and no pair of printable ASCII, `dlig` characters and
       spacing accents, shapes to other glyphs or another width, with kerning and `liga` on
       and off.
     - **12 Feature widths.** Every case item 1 measured, shaped with HarfBuzz under the same
       features and language, is within one font unit of Segoe's width. The coverage cases are
       left out and printed as a count. They are the sequences whose mark Harena UI does not
       map, and the compositions Segoe forms into precomposed letters Open Sans lacks.
       Those sequences include CGJ (U+034F), a mark Open Sans does not map. No font replaces it,
       but Segoe's `ccmp` reads it and draws `i`, `j` and `ị` narrower before it in some faces (at
       most 15 px at 1000 px). Harena UI's `ccmp` cannot read a character it does not map, and this
       milestone adds none. The gate derives those letters and how much narrower per face from item 1's
       measurements. A case before CGJ is left out only with `ccmp` on and off by exactly that
       much; every other case with CGJ must match.
       *Tightened while building:* half a unit, plus each fractionally kerned Segoe pair's own
       rounding (as check 2 holds each pair): a few hundredths of a unit in Text and Display, more
       in Small, which Segoe kerns by fractions. Text and Display measure
       within 0.03 units, so one unit would have let a one-unit error through. The coverage
       cases come to 42 per language: the compositions above, Greek capitals with grave and
       `ϓ`, and `Ơ`/`Ư` with ogonek, where canonical reordering exposes the horn. The
       `font-variant-caps` cases the browser synthesizes are left to item 4.
     - Check 10 also allows only the tables a static TrueType face needs, so no legacy `kern`
       or `morx` table can slip in.
     - Check 2 also holds every stored kern value to Segoe's width for its characters, and
       shapes each default ligature beside each letter across a ZWNJ as well, so a pair is
       checked even where a longer ligature hides it (`ﬀ` + `l`, which ZWNJ or a mark between
       brings back): a wrong value and a missing pair both fail (the third milestone review).
     - Check 12 also requires every ligature `ccmp` forms among the cases, and every glyph the
       build added shaped by one, whatever made it: the seventh milestone review found a widened
       `.ccmp` copy of `Ą` passing because composition hid its rule and no check held its width.
   - The gate is shown failing first, for each of these:
     - a removed feature put back;
     - a `dlig` width off by a unit (and, after the milestone review: a wrong `dlig` form; a
       widened or longer `dlig` context; `dlig` rules reading other text (`abc`, `é`, Cyrillic,
       Greek) or applied everywhere; a dotless character added or dropped);
     - a `frac` numerator off by a unit;
     - an orphan glyph.
4. **In the browser, once, to close.** Each face against its Segoe face in Edge, in DOM at 12,
   14, 16, 20, 28 and 1000 px:
   - item 1's feature matrix;
   - the `dlig` and fraction cases;
   - the base-and-mark matrix, without the coverage cases.

   v0.2's browser check is also rerun, to show the earlier geometry has not moved. Tolerances are
   v0.2's: 0.1%, or one layout unit for a Small face's DOM measurement. The check confirms what
   it measured, not only that nothing failed: the font bytes the page loaded hash to the built
   face's, the faces are the fifteen and the cases all of `data/v0_3/cases.json`, every
   comparison is counted, and Segoe's live widths at 1000 px equal item 1's.

**Out of scope, and where it goes**

- Coverage: the combining marks and precomposed letters Segoe maps and Open Sans does not.
  These need a second Latin source, as in v0.2's note. No consumer needs them yet.
- Segoe's `abvm`. It has no counterpart in Open Sans, and nothing measured here depends on it.
  If item 1 finds a width that does, it comes back into scope.
- `text-transform`, hyphenation and line breaking. The browser does these, not the font. Their
  results are text that the checks above already cover.
- Vertical and East Asian features: v0.4, with Harena UI J.

**Done-when.**
- `python scripts/verify.py` passes checks 1–12 on all fifteen faces. It exits non-zero on any
  failure, and on any of the four mutations under item 3.
- On the guest, item 4 passes within v0.2's tolerances.

**Review.**
- There are three units:
  - measurement (item 1);
  - build and gate together (items 2 and 3), because the v0.2 gate cannot pass a face with
    features removed;
  - browser check (item 4).
- Each unit is reviewed in a separate context before sealing. Build and gate are still reviewed
  separately.
- The guest-side enumeration gets a check of its own: nothing but code points and tag names may
  leave the guest.
- The milestone closes with a reproduction from a fresh clone and a cross-model adversarial
  review.

## v0.2 — every face Edge draws, matched and gated (closed 2026-10-30)

**Goal.** Fifteen static faces — `Harena UI Small`, `Harena UI Text` and `Harena UI Display`, each
in Light, Semilight, Regular, Semibold and Bold — whose geometry is that of the Segoe UI Variable
face Edge draws for the same CSS request, behind the v0.1 gate run over every face.

**What Edge does with Segoe UI Variable** (measured 2026-10-30 on the reference guest, Edge 151,
canvas and DOM agreeing; committed as data by item 1):

- **It draws named instances only.** Each optical size answers every CSS weight from 1 to 1000
  with one of five faces, with the same boundaries in all three sizes: 1–325 → Light, 326–375 →
  Semilight, 376–499 → Regular, 500–649 → Semibold, 650–1000 → Bold. Nothing in between is
  drawn, and `font-variation-settings: 'wght' …` is ignored. These are not CSS matching's
  answers for `@font-face` faces (500 would go down to Regular).
- **Its italic is synthesized.** `font-style: italic` draws an oblique of the upright face with
  identical advances, leaning forward by 1/4 (horizontal per vertical). Segoe UI Variable has
  no italic.
- **Light is reachable** (weights 1–325), though WinUI's type ramp does not use it.
  winui-svelte uses 350, 400, 600 and 700, and italic.
- **Tabular figures are per digit, not one width.** Under `tabular-nums` most faces give all
  ten digits one advance. Which defaults differ from it varies by face: only `1` in Regular,
  Bold and Display Semibold; `1`, `4` and `7` in the Semilight faces and Small and Text Light;
  all ten in Display Light; `1`, `4`, `6` and `9` in Small and Text Semibold, which also leave
  `7` at its default advance, narrower than the other nine. The build follows each digit's
  measured value (`tabular` in `data/v0_2/segoe/`); this is Segoe's behaviour, not a
  measurement to correct.

**Locked — static faces, upright only** ([ADR 0004](docs/adr/0004-static-faces-upright-only.md)):

- *Static, not variable.* The goal is winui-svelte on Linux and macOS laying out as on Windows,
  through `@font-face`. A variable face declared over a weight range is drawn at the requested
  weight (500 as `wght` 500, between two Segoe faces never drawn there), and `@font-face` cannot
  pin `opsz`, so the three sizes would be separate files anyway. Static faces declared over
  Edge's ranges (`font-weight: 500 649` on Semibold, and so on) reproduce the table above for
  every weight, and a page downloads only the faces it uses. *Rejected:* a variable font with
  `wght` (and `opsz`) axes; and a variable font with only some weights, where a missing weight
  is synthesized as faux bold, whose widths are not Segoe's.
- *No italic face.* The browser synthesizes one for Harena UI as it does for Segoe UI Variable,
  so the italic's advances and its oblique look both come out as Segoe's. Shipping Open Sans
  Italic would add fifteen faces whose shapes are not what Windows shows and whose widths would
  have to be forced to upright advances. *Rejected:* an Open Sans Italic cut. This drops the
  "and italic" from the old v0.2 line.
- *The weight ranges* are delivery's to declare, from `data/v0_2/matching.json`, in v0.6. An
  installed (not served) Harena UI is matched by the platform instead; that is checked in 1.0.

**Locked — Light is drawn at Open Sans' lightest.** Segoe's `l` stem at 1000 px is
59 px in Small Light, 45 in Text Light and 30 in Display Light. Open Sans at its lightest
(`wght` 300) is 50 px. Small Light is matched like every other face. Text Light and Display
Light take `wght` 300, the closest Open Sans has, and are heavier than Segoe's. Their geometry
(advances, kerning, metrics) is still Segoe's, which is this project's promise; only colour
differs. *Rejected:* extrapolating Open Sans' masters below 300 (Display Light needs 40% below
the lightest master the designer drew, which is not Open Sans' shape any more), and leaving
Light out (a CSS `font-weight: 300` would then get Semilight's widths).

**Locked — names follow Segoe's three families.** A CSS stack names
`'Segoe UI Variable Text', 'Harena UI Text'`, so `Harena UI Small`, `Text` and `Display` are the
family names on every platform, with the weight as the style. Per face: typographic family
(nameID 16) `Harena UI <size>` and subfamily (17) the weight name; legacy family (1) `Harena UI
<size>` with subfamily (2) `Regular` or `Bold` for those two, and `Harena UI <size> <weight>` with
`Regular` for Light, Semilight and Semibold. `usWeightClass` 300, 350, 400, 600, 700;
`fsSelection` BOLD on Bold and REGULAR on the others. This replaces v0.1's `Harena UI` / `Text`
typographic pair. Extended to more weights, that pair would make `Harena UI Text Semibold` a face
of the family `Harena UI` with the style `Text Semibold`, so where the typographic family is
read (macOS, fontconfig) `font-family: 'Harena UI Text'; font-weight: 600` would not find it.
v0.1's file name, `HarenaUI-TextRegular.ttf`, is kept, and the other faces follow it
(`HarenaUI-DisplaySemibold.ttf`); PostScript names follow v0.1's `HarenaUIText-Regular`.

**In scope**

1. **Measurement, committed.** On the reference guest, with the v0.1 tools:
   - the weight-and-italic table above, every weight 1–1000 per size, from a committed probe,
     as `data/v0_2/matching.json`;
   - advances and pixel ink for every face, including the three Light faces v0 did not
     measure, one file per face (`data/v0_2/segoe/`), which the build reads instead of
     `data/v0_1/segoe-ui-variable.json` (whose target set it keeps);
   - pair kerning for every face, over the v0.1 pair set (v0.1 measured Text Regular only);
   - each digit's advance under `tabular-nums`, for every face;
   - `l` stems for the three Light faces;
   - v0 string widths for the Light faces.
2. **One build, fifteen faces.** `scripts/build.py` builds every face with v0.1's steps,
   unchanged except where this section says. Each face's Open Sans point is chosen by v0.1's
   rule (median ink ratio, then `l` stem), with `wdth` and `wght` clamped to Open Sans' range;
   a clamp is printed and recorded in `data/v0_2/build.json`. Text Light and Display Light are
   the expected clamps. A compiled outline sits on whole units, so its stem jitters by up to
   1 px at 1000 px as `wght` rises. `wght` is therefore the integer whose compiled stem is
   nearest Segoe's within ±15 of the solution, and the gate checks that no integer in that
   window is nearer. This replaces v0.1's fixed 0.3 px tolerance, which Display Bold cannot
   meet at any integer `wght`. The finer search moves Text Regular from v0.1's 399 / 96.1 to
   398 / 96.2: the median ink ratio crosses 1 at `wdth` 96.157, and 398 and 399 compile to
   the same stem. Advances and kerning, which are Segoe's, do not move. Overlaps get one allow-list per face.
3. **Gate over every face.** `scripts/verify.py` runs v0.1's checks 1–8 on each face, with the
   same tolerances and its own reference per face (check 5 now compares every cmap subtable),
   and adds:
   - **9 Tables:** GSUB and GPOS equal the Open Sans instance's, apart from the known
     differences — the `kern` lookup, anchors moved with their glyph, the three unmarked
     accents, the ligature and `one.tnum` copies — compared as tables, not only through shaping
     target text (deferred from v0.1).
   - **10 Faces:** exactly the fifteen files exist, none is italic (no italic bit, no slant) or
     hinted (no hint tables or glyph programs, `gasp` 0x000A), and each face's names, weight
     class and style bits equal the scheme above.
4. **In the browser, once, to close.** v0.1's Done-when 9 for every face, at the five Segoe
   weights, with every DOM measurement also made in `font-style: italic`, which must come out
   at Segoe's italic widths. The served faces are declared at exactly their weight, without
   ranges, so this check covers the geometry of each face and not matching (v0.6).
   *Found while closing:* Segoe's Small faces kern by fractions of a font unit (up to 0.46,
   in 13–18% of pairs); Text and Display kern, and every face advances, in whole units. Why
   Small differs is not measured. A font stores whole units, so those pairs are within half a
   unit (check 2's tolerance), and a short string at a small size can then lay out one layout
   unit (1/64 px) away from Segoe's: `y.` at 12 px is 0.166%. So a Small face's DOM
   measurement passes within 0.1% or within one layout unit. The allowance matters only for
   strings narrower than 15.6 px. The browser check does not guard their widths to a font
   unit (at 1000 px, 0.1% of `y.` is 1.5 units); offline check 2 does, holding every pair
   within half a unit. Canvas, which is not quantized, and the Text and Display faces keep
   0.1%.

**Out of scope, and where it goes**

- `ccmp`, `locl`, `pnum`, `onum`, `lnum` and stylistic sets: v0.3, which measures Segoe under each
  across faces. v0.2 keeps v0.1's behaviour for them.
- Weight-range `@font-face` declarations, WOFF2, npm: v0.6.
- Hinting. Faces stay unhinted with `gasp` 0x000A, as v0.1, whose unhinted face matched Segoe's
  DOM layout to 0.000% at 12–28 px in Edge on Windows. Whether hinting would change that on
  other platforms is unmeasured; it is revisited in 1.0, with rendering quality at UI sizes.
- Coverage beyond Segoe ∩ Open Sans (Segoe maps 1,502 code points Open Sans lacks). Not needed
  by any consumer yet; it would need a second Latin source.
- The roadmap was renumbered when this spec was written: J, Icons and delivery moved from
  v0.3–v0.5 to v0.4–v0.6. Earlier documents (the v0.1 spec, ADR 0003) keep their old numbers.

**Done-when.** `python scripts/verify.py` passes and prints one line per check per face; it
exits non-zero on any failure. v0.1's checks keep their tolerances for every face. The browser
check (item 4) passes on the guest: every measurement within 0.1% of Segoe's, except that a
Small face's DOM measurement may instead be within one layout unit (item 4).

**Review.** Units: measurement (item 1), build and gate (2 and 3), browser check (4), each
reviewed in a separate context before sealing. The build and the gate are sealed together,
because the v0.1 gate cannot pass a fifteen-face build; they are still reviewed separately. The gate is shown failing first: a face missing, an italic
bit set, a GSUB lookup changed for a non-target glyph, and one advance off by a unit in a face
other than Text Regular. The milestone closes with a fresh-clone reproduction and a cross-model
adversarial review.

## v0.1 — one instance, matched and gated (closed 2026-10-30)

**Goal.** `Harena UI Text Regular`: one static TTF built from Open Sans, whose geometry is Segoe
UI Variable Text 400's as Edge draws it (ADR 0001), and an automated gate that fails the build
when it is not.

**In scope**

1. **Coverage, measured first.** Segoe UI Variable's mapped code points are read on the Windows
   machine, as a list of numbers only. The target set is every code point that both Segoe and
   Open Sans map, excluding Private Use, marks (M*), and format and control characters (C*).
   Marks and controls are left out because a mark measured alone is drawn on an inserted
   dotted circle, so its advance is not the font's; that removes 29 code points. Latin
   Extended, Greek and Cyrillic come in through the set, and the v0 comparison is rerun over
   all of it. Segoe advances for the set are measured as in v0. Pair kerning is measured for
   every ordered pair in the set's letters, numbers, punctuation, symbols and spaces (L, N, P, S
   and Z).
2. **Outlines.** Open Sans is instanced at one point: `wdth` where the median, over the target
   set, of Segoe's ink width divided by Open Sans' is 1, then `wght` where its `l` stem at that `wdth` equals Segoe Text
   400's. Each glyph's outline is used unchanged, moved only horizontally.
3. **Spacing.** Each target glyph's advance is Segoe's, rounded to font units. The ink sits where
   its leftover sidebearing splits in Open Sans' own left:right ratio. Where Open Sans' own
   sidebearings are not both non-negative, the ink moves by half the change in advance.
   Under `tnum` every digit takes Segoe's tabular advance. Segoe's default `1` is narrower than
   its tabular one, so `tnum` points at a copy (`one.tnum`). Glyphs outside the target
   set keep Open Sans' spacing, because there is no Segoe number for them.
4. **Kerning.** Segoe's measured pairs become a `kern` feature, which replaces Open Sans' own.
   Open Sans' other GSUB and GPOS features (`liga`, marks and so on) are kept, with three
   consequences found while building:
   - Mark anchors move with their glyph.
   - A default ligature of target characters takes Segoe's width for the same characters.
     Open Sans' ligature glyphs are also U+FB00–FB04's, which Segoe gives widths of their own,
     so the ligature feature points at an exact copy (`fi.liga` and so on). A copy joins every
     mark-attachment lookup its original is in. A letter before or after a ligature kerns as it
     would against the ligature's first or last component.
   - Three spacing Greek accents (U+0384, U+0385, U+1FDE), which Open Sans classes as marks,
     become base glyphs and leave mark attachment, because Segoe and Unicode treat them as
     spacing.
5. **Vertical metrics** are Segoe's numbers: `hhea` 2210/−514/0, `OS/2` typo 1491/−431/269,
   win 2210/514, `USE_TYPO_METRICS` off, all at 2048 units per em, which is also Open Sans'.
6. **Names** are rebuilt, not patched (Harena Term's ADR 0009): family `Harena UI`, subfamily
   `Text`, version `0.1.0`, OFL 1.1, Open Sans' copyright line followed by this project's. No
   name record contains "Segoe" or a reserved name.
7. **Reproducible bytes.** The build reads only pinned sources and stamps `head` from
   `SOURCE_DATE_EPOCH`. `SHA256SUMS` is committed. The gate compares a fresh build against the
   committed file with `git diff --exit-code`, not against a file the build just wrote.

**Out of scope, and where it goes**

- Substitutions other than default ligatures. `ccmp` (for example `i` before a mark above
  becoming dotless) and `locl` (Catalan `l·l`, Romanian `Ş`, NAV/MAH/SRB alternates) put out
  glyphs at Open Sans' or another character's width. In those language tags or decomposed text,
  widths drift from Segoe's: the dotless `i` is 502 units against `i`'s 496, and Catalan `l·l`
  is 557 px against 701 px. What Segoe itself does there has to be measured per language first.
  This goes to v0.2.
- Other non-default numeric features (`pnum`, `onum`, `lnum`) and stylistic sets put out glyphs
  at Open Sans' widths. What Segoe does under each has to be measured first. v0.2.
- A gate check that GSUB and GPOS equal Open Sans' apart from the known differences: the kern
  lookup, anchors moved with their glyph, the three unmarked accents, and the ligature copies.
  Today those tables are checked only through shaping target text, so a change confined to
  non-target glyphs would pass. v0.2, where every instance repeats these edits.

- Other instances, italic and the variable-or-static question: v0.2.
- Hinting. v0.1's gate is about geometry. Whether to hint and how is decided in v0.2, where every
  instance gets the same treatment.
- WOFF2, npm, CI hosting: v0.5. The gate is one local command until the repository has a remote.

**Done-when.** Every item is checked by `python scripts/verify.py`, which exits non-zero on any
failure and prints one line per check. The checks are exhaustive for v0.1. A later version may
add checks but does not loosen these.

1. **Advances:** for every code point in the target set, the advance equals Segoe's measured
   advance, converted to font units, within ±0.5 units.
2. **Kerning:** for every measured pair, the HarfBuzz-shaped width of the pair equals Segoe's
   within ±0.5 units. Pairs Segoe does not kern shape to the sum of their advances. Every run
   that forms a default ligature, after and before every letter, has Segoe's width for the
   same characters. The font's `kern` feature holds no pair beyond Segoe's measured ones.
   **2t:** under `tnum`, every digit has Segoe's tabular advance.
3. **Strings:** every string in `probe/v0/strings.json`, shaped with HarfBuzz, is within 0.1% of
   Segoe's kerned width.
4. **Vertical metrics** equal the item 5 values exactly.
5. **Outlines are Open Sans':** every glyph's contours equal the Open Sans instance's at the
   chosen point, point for point, after one horizontal translation per glyph. A ligature copy
   is compared with the glyph it copies. The point itself is checked to meet item 2, and the
   cmap is Open Sans'. Each glyph's shift is the one item 3's split gives: exact for target
   glyphs, within a unit for copies, and none for glyphs whose advance did not change.
   **5b:** every target letter and default ligature, with each of twelve
   common combining marks, places the mark where Open Sans does relative to the base's ink. A
   mark that does not attach in Open Sans must not attach here either. This is the
   machine form of "Segoe is measured, never copied".
6. **Names:** the records equal item 6. None contains "Segoe", "Selawik", "Source" or
   "Pretendard".
7. **Overlaps are listed, not hidden.** Every glyph whose ink crosses its advance by more than
   5 px at 1000 px beyond what Segoe's own glyph does is named in a committed allow-list. The
   gate fails on any overlap that is not on the list, and on any listed glyph that no longer
   overlaps, so the list cannot go stale.
8. **Reproducible:** two builds give identical bytes, and they equal the committed
   `SHA256SUMS`.
9. **In the browser.** A boundary case the offline checks cannot reach: on the Windows machine,
   in Edge, text set in Harena UI from a served TTF is within 0.1% of the same text in Segoe UI
   Variable Text. This is checked in canvas at 1000 px, and in DOM layout at 12, 14, 16, 20, 28
   and 1000 px. The text is the v0 strings plus `probe/v0_1/dom-strings.json`, which has
   kerning-heavy words, spaces and NBSP, ligatures, Greek, Cyrillic and extended Latin. Digits
   are also checked under `tabular-nums` (`probe/v0_1/browser.py`). This is run once to close v0.1. It is not part of the local
   gate, because it needs the machine.

**Review.** The build and the gate are separate units. Each is reviewed in a separate context
before it is sealed. The gate is shown failing first: one advance off by a unit, one outline
point moved, and one stale allow-list entry each have to make it exit non-zero.

## v0 — feasibility (closed 2026-10-30)

Closed. The answer was no for Inter, and it widened into choosing the sources: Open Sans for
Latin and Pretendard JP for CJK. The spec below is kept as written; the report says where the
work departed from it, which was the ink measurement, stem-matched weights and the candidates.


**Question.** Inter's outlines can be moved but should not be scaled, because scaling changes stem
weight. So the only free variables are sidebearings and kerning. Can those alone reach Segoe UI
Variable's advances?

The deciding quantity is **ink, not advance.** Setting a glyph's advance to Segoe's is always
possible; the question is whether Inter's ink then fits inside it with sidebearings that still
look like type. A glyph whose Inter ink is wider than Segoe's advance cannot be fixed by spacing.

**Measured, on a Windows guest with Segoe installed, in Edge via canvas at 1000 px:**

1. For `Segoe UI Variable Small`, `Text` and `Display`, at `wght` 350, 400, 600 and 700: per glyph,
   for printable ASCII and Latin-1, `width` (advance) and `actualBoundingBoxLeft/Right` (ink).
2. The same for Pretendard JP at the same weights, served from the host with `@font-face`.
3. Kerning: for a pair list (the Latin pairs Pretendard JP kerns, plus the common UI pairs),
   `width(pair) − width(a) − width(b)`.
4. Strings: Gallery-style labels, a pangram, digit runs.
5. The guest's Windows build and the version string and hash of the Segoe font files measured,
   recorded beside the data.

**Method check, before any number is trusted.** Pretendard JP's advances from `measureText` must
equal its `hmtx` (read with fontTools on the host, scaled to 1000 px) to within 0.01 px. This
proves the probe measures the font's metrics and not something the renderer added.

**Report** (`docs/v0-feasibility.md`), per `opsz` × `wght`:

- distribution of advance ratio Segoe / Pretendard (median, IQR, p5, p95, worst ten glyphs);
- distribution of the sidebearing Inter's ink would get inside Segoe's advance, and the glyphs
  where it goes negative;
- string-width error for (a) Pretendard as is, (b) Pretendard with Segoe's advances and its own
  kerning, (c) with Segoe's advances and Segoe's kerning;
- whether the differences between `opsz` instances are spacing-only, which decides whether an
  `opsz` axis can be advance-only (HVAR and GPOS deltas, no outline change).

**Done-when:**

- The data files exist for all 12 Segoe instances and all 4 Pretendard weights, each with the
  provenance of item 5.
- The method check passes, and its result is in the report.
- The report gives the numbers above. It ends with one of the following verdicts, and the verdict
  is locked in an ADR:
  - spacing is enough;
  - spacing is enough except for named glyphs;
  - spacing is not enough, which goes to the owner as a design question: condense the outlines,
    or accept the error.
- No Segoe file has left the guest. Only numbers have.

Italic is not measured in v0. It reuses whichever method v0 validates.
