# AGENTS.md

Operating brief for any AI coding agent working in this repository. Claude Code
reads it through the `CLAUDE.md` symlink beside it.

`harena-ui-font` builds Harena UI, a UI typeface whose shapes come from open
fonts and whose geometry — advance widths, kerning, vertical metrics and icon
ink boxes — is matched to Segoe UI Variable and Segoe Fluent Icons, so that a
layout sized under Segoe comes out the same size under this font. Decisions and
their rationale are in `docs/adr/`; read the ADR before proposing a change it
already settled. `PLAN.md` is the current shape of the work.

Artifacts — code, docs, comments, commit messages — are written in **English**.

## Method

Work follows the `agent-workflow:principles` skill: load it before planning,
reviewing or sealing a unit. Overrides of it are recorded here with their
reason; there are none yet.

If `.private/AGENTS.md` exists, read it: it holds this checkout's operator
preferences. They apply only where these rules and the current task leave a
choice open; on a conflict these rules win, and a consequential conflict is
raised rather than resolved silently. It is input only, under the
private-context rule below.

## Segoe is measured, never copied

Segoe's EULA forbids redistribution. Numbers measured from it — advances,
kerning, vertical metrics, ink boxes — may enter this repository as data. No
Segoe outline, file, or table dump ever does.

## Private context and publishable history

Assume this repository's history will be published. Write tracked content —
code, docs, commit messages — so that opening the repository later requires no
history rewrite. The unit of exposure is the commit, not the working tree:
deleting a file in a later commit publishes it just as surely as leaving it.

Private context lives in `.private/`, untracked. Read it like any other
context, and treat it as **input only** — nothing from `.private/` reaches a
tracked file, commit message, PR, or issue unless it is first restated in a
form that would be fine published.

**Run this once per clone**, before the first commit from it:

```sh
git config core.hooksPath .githooks
```

`.gitignore` stops an accidental `git add .`; the tracked `.githooks/pre-commit` is the layer
that survives `git add -f`. That hook only runs if `core.hooksPath` points at it, and git
does not carry local config across a clone — so a fresh clone starts with the guard off,
silently.
