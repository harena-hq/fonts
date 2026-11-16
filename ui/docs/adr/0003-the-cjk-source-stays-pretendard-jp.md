# 0003 — The CJK source stays Pretendard JP, set to the browser's widths

Status: **locked**, 2026-10-30. Evidence: `docs/v0-feasibility.md`, `data/v0/cjk-windows.json`,
and the specimen from `probe/v0/specimen.py`.

## Context

With Latin moved to Open Sans (ADR 0002), Pretendard JP's CJK lost one reason to be the source:
it had been tuned to sit beside Inter. Noto Sans CJK is the natural partner of Open Sans' own
lineage. Its Hangul and Han are the same drawings as Pretendard JP's, since both come from Source
Han Sans; its kana differ. Pretendard JP's are from M PLUS 1p.

ADR 0001 sets the target. Edge draws every CJK character under a Segoe stack at 1 em: Hangul in
Malgun Gothic, Japanese in Yu Gothic. Neither candidate is drawn that way:

- Pretendard JP: Hangul 0.864 em, kana and Han 0.938 em;
- Noto Sans KR: Hangul 0.920 em;
- Noto Sans JP: kana and Han 1 em.

Glyph bodies against the Windows faces, median ink width:

| script | Pretendard JP | Noto Sans |
|---|---|---|
| Hangul | −8% | −5% |
| kana | +5% | +7% |
| Han | −2% | +5% |

## Decision

**Harena UI J's Hangul, kana and Han come from Pretendard JP.**

- Every CJK advance is set to 1 em, the browser's.
- Hangul is scaled uniformly by about 1.08 to Malgun Gothic's body, and its stem growth is
  compensated through `wght`, as Harena Term did (its ADRs 0002 and 0003). Kana and Han keep
  their size and gain space only.
- Weights are matched to the Windows faces' stems: Malgun Gothic's `ㅣ` for Hangul, Yu Gothic's
  `十` for Japanese.

The deciding reason is **consistency with Harena Term**. Harena Term's CJK is Pretendard JP
(its ADR 0005), and the two families are meant to be used together. Pretendard JP also carries
Hangul, kana and Japanese-form Han in one source, where Noto would need KR and JP merged. Its
kana and Han bodies are also closer to Yu Gothic's.

## Rejected, and what it costs

- **Noto Sans KR + JP.** To the owner's eye, Noto's shapes are closer to what Windows draws.
  That is recorded here because it is the strongest argument against this decision. Reopen it if
  pairing with Harena Term stops mattering.
- **Keeping Pretendard JP's own widths.** Its Hangul is set tight: about half the spacing of a
  full-width cell, which is the reason many Korean UIs choose it. Keeping that would make a
  Korean label about 14% shorter than on Windows, and a Japanese one about 6% shorter. That
  breaks the project's one promise. At 1 em, Hangul spacing roughly doubles and becomes Malgun
  Gothic's.

## Consequences

- Harena UI J does not look like Pretendard. It is Pretendard JP's drawings at Windows' widths.
- The 1.08 Hangul scale and the weight mapping were v0.4's to verify against a built font, not
  against the CSS approximation the specimen used. Measured, the scale that reaches Malgun Gothic's
  body differs by weight: 1.099 at Light and Semilight, 1.09 at Regular, 1.066 at Semibold and Bold
  (`data/v0_4/build.json`).
