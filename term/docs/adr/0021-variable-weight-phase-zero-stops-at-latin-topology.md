# 0021 — Variable-weight Phase 0 stops at the Latin topology

Status: **accepted feasibility result**. Reopen if Iosevka gains a compatible
variable source product, or if a deterministic topology harmoniser can preserve
both endpoints within the tolerances below without manual redrawing.

## Question

Could Harena Term replace each regional Regular/Bold pair with one `wght`
400–700 variable font by rebuilding Iosevka from source and using Pretendard
JP's existing variable axis?

The earlier rejection in [PLAN.md D6](../../PLAN.md#d6--no-variable-weight) measured released Iosevka Term Nerd Font binaries.
The source-built HarenaLatin endpoints had not been tested with a complete
interpolatability checker, so rebuilding the Latin was a materially different
proposal rather than a repetition of that experiment.

## Gate

[`scripts/vf_phase0.py`](../../scripts/vf_phase0.py) trims the unhinted
HarenaLatin Regular and Bold masters exactly as the shipping build does, then
runs FontTools' `varLib.interpolatable` over the resulting glyph set. The gate
is deliberately before CJK grafting: an incompatible base cannot become
compatible by adding more glyphs or an intermediate master.

The input files are:

- `HarenaLatin-Regular.ttf`, Iosevka `shape = 500`, CSS weight 400;
- `HarenaLatin-Bold.ttf`, Iosevka `shape = 800`, CSS weight 700.

Both are unhinted. Hint programs index points and would add noise to a question
about whether the outlines themselves can interpolate. The shipping build reads
the hinted masters, but `trim_base` selects glyphs from the `cmap` and its
`ccmp` closure, neither of which hinting changes, so the trimmed glyph set is
the same.

## Result

Measured in August 2026 against Iosevka v34.8.0 (`ca3ad8e`). Each trimmed
master contains **11,699 glyphs**. FontTools reports **3,620 problems across
1,864 glyphs**:

| problem | count |
|---|---:|
| node count | **2,013** |
| node incompatibility | **776** |
| wrong start point | 316 |
| underweight interpolation | 232 |
| kink | 159 |
| path count | **99** |
| contour order | 25 |

The boldface categories are structural. Start points and contour order can be
canonicalised without changing a drawing, but a different path count, point
count, or on/off-curve sequence requires constructing a shared topology. The
failures include ordinary text glyphs such as `B`, `C`, `G`, `M`, `O`, `Q`,
`ampersand`, and `Euro`; this is not a remote-symbol-only tail that could be
frozen without changing the face.

The audit needs the small `munkres` assignment solver because FontTools refuses
contour matching above six contours without either it or SciPy. It is pinned in
[`requirements-audit.txt`](../../requirements-audit.txt), outside the shipped
build's pins; using SciPy for a seven-kilobyte assignment problem would be the
larger dependency.

## Decision

Stop the variable-font build at Phase 0. Do not construct `fvar`/`gvar`, graft
CJK, change packaging, or replace the four static release faces.

The rejected shortcut is to feed the two masters to varLib despite the report.
An intermediate master can improve a curve only after every master has the same
topology; it cannot repair incompatible endpoints.

## Follow-up: static-to-variable reconstruction

The [`static-to-variable`](https://github.com/mblode/static-to-variable) 0.6.1
reconstruction pipeline was also tested outside the repository against the same
Regular and Bold donors, in August 2026. Nothing in this repository re-runs it,
so the numbers in this section are a record, not a gate. It can manufacture compatible outlines and produce a
400–700 variable font, but that result does not overturn the decision above.

The pipeline reconstructed 2,945 of 11,693 donor glyphs. At `wght=550`, the
generated instance was compared with an Iosevka source build at the corresponding
`shape=650`. All 7,582 encoded characters and every advance width matched. For
ASCII, the median outline-area difference was 0.61%, the maximum was 1.85%, and
a representative terminal string produced no pixel difference of alpha 32 or
greater at 13 px. This is promising for ordinary terminal text.

The full repertoire was not release quality. At the same midpoint, 1,600 encoded
characters exceeded 1% outline-area difference and individual mathematical or
symbol glyphs reached 15–45%. FontTools also continued to report interpolation
warnings involving underweight contours and start points. Freezing a small list
of known failures was insufficient as a general quality policy.

Nor did two-weight web packaging benefit: the reconstructed VF was 2,926,736
bytes as TTF and 764,672 bytes as WOFF2, compared with 2,644,308 and 631,960
bytes respectively for the two static donors combined. A continuous axis may
amortise its cost when three or more intermediate weights are actually shipped;
it is not a size optimisation for Harena Term's current Regular/Bold terminal
use.

Version 0.6.1 also attempted reconstruction before applying its documented
per-glyph freeze strategy, so five known-incompatible glyphs caused the stock
command to abort. The feasibility run used a temporary one-line ordering fix;
no patched third-party code or generated font is part of this repository.

## What would reopen it

One of these must exist first:

1. an upstream Iosevka variable/interpolatable source product that preserves the
   Harena metric overrides; or
2. a deterministic whole-cohort harmoniser that resolves every structural
   problem with no manual redraw, exact advances and bounds, outline-area delta
   at most 0.1%, Hausdorff distance at most one font unit, and 256-ppem alpha
   mask disagreement at most 0.1% of nonempty pixels.

Anything less would trade the measured static endpoint quality for the presence
of an axis. The project does not do that silently.

## Separate distribution question

This result says nothing against keeping K and J as separate variable files if
the Latin blocker is later solved. It also does not decide a web-only common
glyph plus regional fallback split. That changes CSS selection and download
composition rather than outline interpolation and remains a separate task.
