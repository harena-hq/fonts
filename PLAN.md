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
| **Harena UI** | Latin, Greek, Cyrillic, punctuation, symbols | Open Sans ([ADR 0002](docs/adr/0002-the-latin-source-is-open-sans.md)) | Segoe UI Variable as Edge draws it — advances, kerning, vertical metrics, per named instance ([ADR 0001](docs/adr/0001-the-target-is-segoe-as-the-browser-draws-it.md)) |
| **Harena UI J** | Harena UI, plus Hangul, Kana and Han | Latin as Harena UI; CJK from Pretendard JP ([ADR 0003](docs/adr/0003-the-cjk-source-stays-pretendard-jp.md)) | Latin as Harena UI; CJK at the browser's fallback widths (1 em) and Malgun Gothic / Yu Gothic bodies and stems |
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

## Roadmap

| version | one goal |
|---|---|
| **v0** ✓ | Know, with numbers, whether spacing alone can bring Pretendard JP's Latin to Segoe UI Variable's widths. Answered in `docs/v0-feasibility.md`; ADRs 0001–0003 |
| **v0.1** ✓ | One static Harena UI instance (Text, 400) whose string widths match Segoe within tolerance, behind an automated gate. Closed 2026-10-30: gate passes, and in Edge on Windows all 589 browser measurements (canvas and DOM at 12–1000 px) are within 0.000% of Segoe |
| **v0.2** ✓ | Every face Edge can draw from Segoe UI Variable — Small, Text and Display, each at Light, Semilight, Regular, Semibold and Bold — as a static Harena UI face matched to it, behind the same gate. Closed 2026-10-30: gate passes over all fifteen faces; in Edge on Windows, 17,115 measurements are within 0.1% of Segoe, six Small-face DOM ones within one layout unit instead (item 4) |
| v0.3 | Every OpenType feature and language a browser can request lays each face out at Segoe's widths: the features Segoe has are matched, the ones it lacks are removed |
| v0.4 | Harena UI J |
| v0.5 | Harena UI Icons |
| v0.6 | Delivery: WOFF2 split by `unicode-range`, npm package with a CSS entry |
| 1.0 | Verified on Windows, macOS and Linux against Segoe layouts |

Each version's spec is written when the previous one closes. v0.3's is current; the earlier ones
are kept below it.

## v0.3 — every feature a browser can request, at Segoe's widths

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
