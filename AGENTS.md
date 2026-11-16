# AGENTS.md

Operating brief for any AI coding agent working in this repository. Claude Code
reads it through the `CLAUDE.md` symlink beside it.

This repository holds two typefaces, each in its own directory: Harena Term in
`term/` and Harena UI in `ui/`. Work on one starts from its directory's own
`AGENTS.md`, which holds that family's rules, `PLAN.md` and `docs/adr/`. The
rules below hold for both. Decisions about the repository itself are in
`docs/adr/` at the root, cited as "fonts ADR NNNN", since each family numbers
its own ADRs from 0001.

Artifacts — code, docs, comments, commit messages — are written in **English**.

## Private context and publishable history

Assume this repository's history is public, as it is. Write tracked content —
code, docs, commit messages — so that publishing it requires no history
rewrite. The unit of exposure is the commit, not the working tree: deleting a
file in a later commit publishes it just as surely as leaving it.

Private context lives in a `.private/` directory, untracked, at the root or in
a family's directory. Read it like any other context, and treat it as **input
only** — nothing from it reaches a tracked file, commit message, PR, or issue
unless it is first restated in a form that would be fine published.

**Run this once per clone**, before the first commit from it:

```sh
git config core.hooksPath .githooks
```

`.gitignore` stops an accidental `git add .`; the tracked `.githooks/pre-commit`
is the layer that survives `git add -f`. It refuses a staged path under any
`.private/` and a staged font binary, since fonts are fetched or built, never
committed. That hook only runs if `core.hooksPath` points at it, and git does
not carry local config across a clone — so a fresh clone starts with the guard
off, silently.

## History

Neither family's history was rewritten when they were joined (fonts ADR 0001):
each moved into its directory by a commit that only renames. `git log --follow`
across the join mixes in the other family's commits for a path both once had
(`PLAN.md`, `README.md`, `scripts/build.py`); start it from the family's own
history to see one: `git log --follow <family's move commit> -- ui/PLAN.md`.
