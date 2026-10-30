# v0 — which Latin source fits Segoe UI Variable's geometry

Measured 2026-10-30. The data is in `data/v0/`; the provenance of every Segoe number is in each
file's `provenance`. To reproduce:

1. `scripts/fetch_sources.sh`, and `pip install -r requirements.txt` (Python 3.12). Node 24
   (`.nvmrc`); the probes use its built-in `WebSocket`.
2. On a Windows machine with Segoe UI Variable, run Edge with a remote-debugging port. Serve
   this repository's root over HTTP where that Edge can reach it, because `probe/page.html`
   loads `../sources/`.
3. `python probe/v0/run.py <cdp-base> <repo-root-url> <provenance.json>` and
   `python probe/v0/cjk.py` with the same arguments. These write the Segoe and Windows CJK data.
   `run.py`'s docstring gives the provenance file's fields.
4. `python probe/v0/analyze.py --detail` runs offline and prints every number below except the
   CJK section's. Those come from `data/v0/cjk-windows.json` and the candidate files.
5. `python probe/v0/specimen.py`, then `node probe/shot.mjs <cdp-base>
   <repo-root-url>/build/specimen.html <out.png>`, gives the CJK specimen.

## The question, restated

PLAN.md asked whether spacing alone (sidebearings and kerning) can bring Pretendard JP's Latin,
which is Inter, to Segoe UI Variable's advances. Partway through, the question widened to
**which open Latin source needs the least change to fit Segoe's geometry**, since nothing ties
Harena UI's Latin to Inter. Candidates:

- **Inter**, as carried by Pretendard JP v1.3.9 (the original plan);
- **Open Sans** and **Noto Sans**, the Droid Sans lineage, both variable in `wght` and `wdth`;
- **Selawik** 1.01, Microsoft's open fallback for Segoe UI, as a control.

## Method

- **Segoe** (`SegUIVar.ttf` "Version 2.03") was measured in Edge on Windows 11 25H2, at 1000 px:
  advances, pair kerning and string widths from canvas `measureText`; ink boxes from pixels.
- **`measureText`'s ink box is not usable.** `actualBoundingBox*` come back rounded outward to
  1/64 em: 15.625 px at 1000 px. All 14,898 ink values in a first pass sat on that grid. Ink is
  therefore read from pixels: the outermost covered column, refined by its coverage.
- **Candidates** were read from their files with fontTools (advances, `glyf` bounds) and shaped
  with HarfBuzz (strings). Only Segoe needs the browser.
- **Method check**, on Pretendard JP at `wght` 400, whose exact answer fontTools gives:
  - Browser advances equal `hmtx` to a worst case of 0.005 px.
  - Pixel ink equals the outline's tight bounds to a median of 0.01 px. The worst case is
    0.53 px.
  - The reference is the drawn outline. The bounding box stored in `glyf` also bounds off-curve
    points; for `£` it overstates the ink by 8 px.
- **Edge fixes a named instance's `opsz`.** Each Segoe instance's width per 1000 px was measured
  in 21 conditions: canvas and DOM, sizes from 8 to 1000 px, `font-optical-sizing: none`, and
  explicit `opsz` settings. The spread is at most 0.011% (`opsz-check.json`). So measuring at
  1000 px measures the instance that a 14 px label gets.
- **Weights are matched by stem, not by number.** The vertical stem of `l` and `I` was measured
  from pixels for every Segoe instance and across each candidate's `wght` range. Each candidate is
  compared at the weight whose stems match. Equal numbers do not give equal stems. Segoe at
  350 has `l` stems of 73, 62 and 51 px in Small, Text and Display. Inter matches those at `wght`
  337, 279 and 218.
- **"Spacing kept"** for a glyph is the candidate's ink placed in Segoe's advance: the total
  sidebearing left, divided by the candidate's own. 1 means the candidate's spacing is unchanged;
  0 means its ink touches both edges.
- **Overlaps** are glyphs whose ink would cross the advance by more than 5 px beyond what Segoe's
  own glyph does.

## Results

All 12 Segoe instances (Small, Text and Display × 350, 400, 600 and 700) are pooled. Each
column is the median over instances of a per-instance statistic.

| candidate | wdth | advance S/C | ink S/C | spacing kept p50 | p5 | overlaps | string error |
|---|---|---|---|---|---|---|---|
| Inter (Pretendard JP) | 100 | 0.981 | 0.981 | 0.857 | 0.053 | 11 | +2.26% |
| Open Sans | 100 | 0.965 | 0.973 | 0.778 | −0.054 | 14.5 | +5.64% |
| **Open Sans** | **95** | **1.013** | **1.019** | **1.053** | **0.485** | **6** | **+0.52%** |
| Open Sans | 90 | 1.062 | 1.071 | 1.326 | 0.743 | 4 | −4.98% |
| Noto Sans | 100 | 0.963 | 0.973 | 0.775 | −0.158 | 15.5 | +5.41% |
| Noto Sans | 95 | 0.999 | 1.007 | 0.985 | 0.259 | 9 | +1.86% |
| Selawik | 100 | 1.000 | 1.000 | 0.998 | 0.960 | 4.5 | +0.69% |

"String error" is each candidate as it ships, with its own kerning, against Segoe. It shows how
far apart the two are before any change. Harena UI will carry Segoe's advances and kerning, so
its string widths match by construction. **The verdict rests on the ink fit, not on this column.**

At Segoe UI Variable Text 400, per candidate:

| candidate | wght | advance S/C | spacing kept p50 / p5 | overlaps |
|---|---|---|---|---|
| Inter | 374 | 0.981 | 0.874 / 0.166 | `J T Y _ ¤ Æ Î Ï Ý î ï` |
| Open Sans wdth 95 | 396 | 1.002 | 1.048 / 0.486 | `* _ f ¯ Î î` |
| Noto Sans wdth 95 | 375 | 0.989 | 0.943 / 0.302 | `* _ f { } ¯ Î î` |
| Selawik | 400 | 1.000 | 1.000 / 1.000 | `Î Ï ï` |

### Inter needs the most change

- Inter's glyphs are about 2% wider than Segoe's in ink and in advance. Fitting Segoe's advances
  leaves Inter a median 86% of its spacing.
- The tail is the problem. About eleven glyphs per instance cannot fit without overlapping.
  `Y` and `Ý` are among them in every instance, and `J` in nine of twelve. The p5 of spacing
  kept is near zero.
- Spacing alone is not enough for Inter.

### Open Sans at `wdth` 95 fits with almost no change

- Its advances and ink are within 2% of Segoe's, and it keeps its own spacing (p50 1.05).
- **At Small, and at Text 350 to 600,** its overlaps are glyphs that overhang by design: `f`,
  `_`, `¯`, `*`, and the circumflexes over a narrow `I`.
- **Elsewhere there are a few more.** Text 700 adds `v w y ý ÿ`. Display adds `x`, `{ }` or
  `w`, depending on the weight. These are the glyphs where the per-instance `wdth` has to sit
  wider than 95, or where kerning has to absorb the difference.
- Narrowing to `wdth` 95 uses the designer's own narrow masters, not scaled outlines. It thins
  the `l` stem by 1.5% (80.3 to 79.0 px at `wght` 396), which about six units of `wght` restore.
- Open Sans is variable in `wght` (300–800) and `wdth` (75–100), has an italic, and covers
  Greek and Cyrillic. It is OFL 1.1 with no Reserved Font Name.

### Noto Sans at `wdth` 95 is second

Noto Sans is the same lineage as Open Sans. At the same width it keeps less spacing (p5 0.26
against 0.49) and has more overlaps.

### Selawik matches but cannot be the source

- At Text 350, 400 and 700, Selawik's advances and ink equal Segoe UI Variable Text's to within
  0.1%. It is a geometric twin of the Text instance.
- It cannot be the source, for these reasons:
  - It has 352 glyphs, mapping 348 characters. Three Latin-1 characters are missing (U+00A0,
    U+00AA, U+00BA), and it covers 103 of the 128 characters in Latin Extended-A.
  - It has no Greek, no Cyrillic and no italic.
  - Its five weights are not interpolation-compatible. Contour structure differs from Regular
    in 408 of 1,408 glyph comparisons, so no variable font can be built from them.
  - Its last release was 1.01, in 2015.
- It confirms the measurement: a font made to stand in for Segoe measures as Segoe.

### Segoe's optical sizes change shapes, not only spacing

Small against Text, at the same weight:

| weight | advance | ink |
|---|---|---|
| 350 | +4.3% | +3.4% |
| 400 | +3.3% | +1.8% |
| 600 | +2.7% | +0.7% |
| 700 | +1.5% | −0.5% |

Display against Text: the advance is −1.3% to −2.7% and the median ink is unchanged, except at
350 (−2.3%). Stems also change with optical size at 350 (73, 62 and 51 px).

So an `opsz` axis in Harena UI cannot be spacing alone. With Open Sans it does not need to be:
each Segoe instance maps to its own point in Open Sans' `wght` × `wdth` space. Wider and heavier
gives Small; narrower and lighter gives Display at 350. That is real outline variation from the
designer's masters.

## Verdict

**Spacing is not enough for Inter. A different Latin source makes it unnecessary.** Open Sans,
with each Segoe instance mapped to a stem- and width-matched point in `wght` × `wdth`, fits
Segoe's advances with its own spacing intact. Segoe's advances and kerning are then applied as
data. The remaining overlaps are mostly glyphs that overhang by design; the bold Text and the
Display instances have a few more, listed above.

The owner chose Open Sans; it is locked in
[ADR 0002](adr/0002-the-latin-source-is-open-sans.md).

## CJK: what Windows draws, and which source fits it

Segoe UI Variable has no Hangul or Kana. What a layout under Segoe gets for them is whatever the
platform falls back to. That fallback is the geometry Harena UI J has to reproduce. Measured in
the same Edge, with `font-family: "Segoe UI Variable Text"` and CDP
`CSS.getPlatformFontsForNode` naming the face that drew each string (`data/v0/cjk-windows.json`):

| `lang` | Korean strings | Japanese strings |
|---|---|---|
| `ko` | Malgun Gothic | Malgun Gothic (some MS PGothic, Yu Gothic) |
| `ja` | Malgun Gothic | **Yu Gothic** |
| `en` | Malgun Gothic | Yu Gothic, mixed with Microsoft YaHei for Han |

- **The browser falls back to Yu Gothic, not Yu Gothic UI.** WinUI's own text stack uses Yu
  Gothic UI, whose kana are proportional (p5–p95 0.62–0.86 em) and whose CJK punctuation is half
  width. That is native WinUI's geometry, not the web's. This project's consumer is a CSS stack,
  so the browser's geometry is the target. A native-WinUI target would need its own decision.
- **Every CJK advance the browser draws is 1 em.** That holds for Malgun Gothic's 11,172 Hangul
  syllables and for Yu Gothic's kana, Han and punctuation.

Candidate advances, from the files: Pretendard JP draws Hangul at 0.864 em and kana and Han at
0.938 em. Noto Sans KR draws Hangul at 0.920 em. Noto Sans JP draws kana and Han at 1 em. Neither
candidate's Hangul is full width.

**Widening to 1 em is always possible.** It only adds space. The open question is how large the
glyph bodies are against the Windows faces. Medians are of a sample of common characters, ink
width × height, from pixels for Windows and from the outlines' tight bounds for the candidates:

| script | Windows | Pretendard JP, as drawn | Noto Sans, as drawn |
|---|---|---|---|
| Hangul | Malgun 862 × 942 | 795 × 868 (−8%) | KR 820 × 904 (−5%) |
| Kana | Yu Gothic 755 × 786 | 789 × 788 (+5%, 0%) | JP 807 × 822 (+7%, +5%) |
| Han | Yu Gothic 884 × 886 | 866 × 860 (−2%, −3%) | JP 926 × 919 (+5%, +4%) |

- **Japanese:** Pretendard JP's kana and Han are already within 0–5% of Yu Gothic's body. So the
  widening is spacing only. Noto Sans JP's are 4–7% larger.
- **Hangul:** both candidates are smaller than Malgun Gothic. Pretendard JP scaled uniformly by
  about 1.08 matches Malgun's body. Its advance then reaches 0.937 em, and spacing fills the rest
  to 1 em. The stem growth from scaling is compensated through `wght`, as Harena Term did
  (its ADRs 0002 and 0003).
- **One source:** Pretendard JP carries Hangul, kana and Japanese-form Han in one file. With
  Noto, Hangul would come from KR and kana and Han from JP: two sources to merge, and two sets of
  instancing and weight matching.

**CJK verdict:** keep Pretendard JP for Harena UI J's CJK. Set its advances to the browser's
1 em. Scale Hangul by about 1.08 to Malgun Gothic's body; leave kana and Han at their size. The
owner chose this over Noto Sans KR and JP for consistency with Harena Term, while judging Noto's
shapes closer to Windows'. It is locked in
[ADR 0003](adr/0003-the-cjk-source-stays-pretendard-jp.md).

## Limits

- **Coverage.** Printable ASCII and Latin-1 only. Latin Extended, Greek and Cyrillic are not yet
  compared.
- **Stems at narrower widths.** Stems were matched at `wdth` 100. The 1.5% thinning at 95 was
  checked for Open Sans `l` only.
- **Kerning.** The pairs are those of a fixed set plus every character the strings use.
  Contextual kerning, if Segoe has any outside that set, is not measured.
- **Segoe file.** The numbers are for `SegUIVar.ttf` "Version 2.03", SHA-256 `27ca1ab4…0f682`.
  Another version of the file needs measuring again.
