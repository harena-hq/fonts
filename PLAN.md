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
| v0.2 | Every face Edge can draw from Segoe UI Variable — Small, Text and Display, each at Light, Semilight, Regular, Semibold and Bold — as a static Harena UI face matched to it, behind the same gate |
| v0.3 | Substitution and numeric features (`ccmp`, `locl`, `pnum`, `onum`, `lnum`, stylistic sets) at Segoe's widths |
| v0.4 | Harena UI J |
| v0.5 | Harena UI Icons |
| v0.6 | Delivery: WOFF2 split by `unicode-range`, npm package with a CSS entry |
| 1.0 | Verified on Windows, macOS and Linux against Segoe layouts |

Each version's spec is written when the previous one closes. v0.2's is current; v0.1's and v0's
are kept below it.

## v0.2 — every face Edge draws, matched and gated

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
v0.1's file name, `HarenaUIText-Regular.ttf`, is kept, and the other faces follow it.

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
   the expected clamps. Overlaps get one allow-list per face.
3. **Gate over every face.** `scripts/verify.py` runs v0.1's checks 1–8 on each face, with the
   same tolerances and its own reference per face, and adds:
   - **9 Tables:** GSUB and GPOS equal the Open Sans instance's, apart from the known
     differences — the `kern` lookup, anchors moved with their glyph, the three unmarked
     accents, the ligature and `one.tnum` copies — compared as tables, not only through shaping
     target text (deferred from v0.1).
   - **10 Faces:** exactly the fifteen files exist, none is italic (no italic bit, no slant), and
     each face's names, weight class and style bits equal the scheme above.
4. **In the browser, once, to close.** v0.1's Done-when 9 for every face, at the five Segoe
   weights, plus two cases on Text Regular: `font-style: italic` comes out at Segoe's italic
   widths, and the served faces are declared without weight ranges, so this check covers the
   geometry of each face and not matching (v0.6).

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
check (item 4) passes on the guest: every measurement within 0.1% of Segoe's.

**Review.** Units: measurement (item 1), build (2), gate (3), browser check (4), each reviewed in
a separate context before sealing. The gate is shown failing first: a face missing, an italic
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
