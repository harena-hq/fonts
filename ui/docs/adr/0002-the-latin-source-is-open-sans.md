# 0002 — The Latin source is Open Sans, not Inter

Status: **locked**, 2026-10-30. Evidence: `docs/v0-feasibility.md`, data in `data/v0/`.

## Context

The plan took Harena UI's Latin from Pretendard JP, which is Inter. v0 asked whether spacing
alone could bring it to Segoe UI Variable's advances. It cannot. Inter's glyphs are about 2%
wider than Segoe's in ink. Fitting Segoe's advances leaves a median 86% of Inter's spacing, and
about eleven glyphs per instance, `J`, `Y` and `Ý` among them, cannot fit without overlapping.

The question was widened to the Droid Sans lineage, Segoe's nearest open relatives, with
Selawik as a control. Each candidate was compared with each Segoe instance at the weight whose
vertical stems match.

## Decision

**Harena UI's Latin is drawn from Open Sans** (`OpenSans[wdth,wght]` and its italic, OFL 1.1, no
Reserved Font Name).

- Each Segoe named instance maps to its own point in Open Sans' `wght` × `wdth` space. The
  `wght` comes from the stem match. The `wdth` is near 95 for Text, wider for Small and narrower
  for Display.
- At `wdth` 95, Open Sans' advances and ink are within 2% of Segoe's, and it keeps its own
  spacing: median 1.05 of it, p5 0.49.
- At Small and at Text 350–600, the only overlaps are glyphs that overhang by design: `f`, `_`,
  `¯`, `*` and `Î`. Text 700 and Display add a few: `v w y ý ÿ`, `x`, `{ }` and `w`. Those are
  for each instance's own `wdth` and for kerning to absorb.
- Narrowing uses the designer's own narrow masters, not scaled outlines. The 1.5% stem thinning
  at `wdth` 95 is restored through `wght`, about six units.
- Segoe's advances and pair kerning are then applied as data.
- Segoe's optical sizes change shapes as well as spacing; Small is 3.4% wider in ink at 350. So
  Harena UI's `opsz` is a mapping onto Open Sans' axes, not a spacing-only axis.

## Rejected

- **Inter.** It overlaps in the tail and keeps less of its spacing, as above.
- **Noto Sans.** It is the same lineage as Open Sans but keeps less spacing at the same width
  (p5 0.26 against 0.49), and it has more overlaps.
- **Selawik.** It is a geometric twin of Segoe UI Variable Text; its advances and ink are
  within 0.1%. It still cannot be the source:
  - It has 352 glyphs mapping 348 characters, and no Greek, Cyrillic or italic.
  - Its five weights are not interpolation-compatible, so no variable font can be built.
  - Its last release was in 2015.
- **Scaling Inter's outlines.** That changes stem weight, the distortion the plan set out to
  avoid.

## Consequences

- Pretendard JP no longer supplies Latin. It stays the CJK source (ADR 0003).
- Harena UI's Latin no longer matches Harena Term's Latin, which is Iosevka. They never did: a
  monospace and a UI face are different designs.
- Latin Extended, Greek and Cyrillic have not been compared yet. v0.1's spec includes them.
