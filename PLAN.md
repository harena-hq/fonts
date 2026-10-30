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
| v0.1 | One static Harena UI instance (Text, 400) whose string widths match Segoe within tolerance, behind an automated gate |
| v0.2 | The full `opsz` × `wght` (350/400/600/700) matrix and italic, in the form v0 decides (variable or static) |
| v0.3 | Harena UI J |
| v0.4 | Harena UI Icons |
| v0.5 | Delivery: WOFF2 split by `unicode-range`, npm package with a CSS entry |
| 1.0 | Verified on Windows, macOS and Linux against Segoe layouts |

Each version's spec is written when the previous one closes. Only v0's is below.

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
