# 0004 — Fifteen static faces, upright only

Status: **locked**, 2026-10-30. Evidence: the v0.2 spec in `PLAN.md`; `data/v0_2/matching.json`.

## Context

The roadmap left v0.2's form open: one variable font with `wght` and `opsz` axes, or static
instances, and an italic. The project's purpose decides it: winui-svelte on Linux and macOS
has to lay out as it does on Windows, and it gets Harena UI there through `@font-face`.

Measured in Edge 151 on Windows 11, canvas and DOM agreeing (`data/v0_2/matching.json`):

- Edge draws Segoe UI Variable's named instances only. In each optical size, CSS weights
  1–325 draw Light, 326–375 Semilight, 376–499 Regular, 500–649 Semibold and 650–1000 Bold.
  `font-variation-settings: 'wght' …` is ignored.
- Segoe UI Variable has no italic. `font-style: italic` draws an oblique of the upright face,
  leaning forward by 1/4, with the upright advances.
- The three optical sizes are separate family names (`Segoe UI Variable Small`, `Text`,
  `Display`), and Edge pins each one's `opsz` whatever the font size (v0).

## Decision

**Harena UI is fifteen static faces** — Small, Text and Display, each in Light, Semilight,
Regular, Semibold and Bold — **and has no italic face.**

- Each face is matched to the Segoe face Edge draws for the same request.
- Served faces are declared over Edge's weight ranges (`font-weight: 500 649` on Semibold, and
  so on), so every CSS weight reaches the face Segoe's would.
- Italic is left to the browser, which synthesizes it for Harena UI as it does for Segoe UI
  Variable: the advances stay upright, as Segoe's do.
- Text Light and Display Light are drawn at Open Sans' lightest master (`wght` 300) and are
  heavier than Segoe's, whose stems Open Sans does not reach. Their geometry is still Segoe's.

## Rejected

- **A variable font over a weight range.** The browser draws it at the requested weight, so
  `font-weight: 500` would be `wght` 500, between two Segoe faces that are never drawn there.
- **A variable font with only some weights.** A missing weight is synthesized as faux bold,
  whose widths are not Segoe's.
- **An `opsz` axis.** `@font-face` cannot pin it per family name, so the three sizes would be
  three files anyway.
- **An Open Sans Italic cut.** Its shapes are not what Windows shows, and its widths would have
  to be forced to the upright advances.
- **Extrapolating Open Sans below `wght` 300** for the light faces. Display Light needs 40%
  below the lightest master the designer drew.
- **Leaving Light out.** A request for weight 300 would get Semilight's widths.

## Consequences

- v0.2 drops "and italic" from its roadmap line.
- Delivery (v0.6) declares the weight ranges from `data/v0_2/matching.json`.
- An installed, not served, Harena UI is matched by the platform; 1.0 checks that on Linux and
  macOS.
- Names follow Segoe's three families: `Harena UI Small`, `Text` and `Display`, weight as style.
