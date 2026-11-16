# 0001 — One repository for Harena's fonts

Status: **locked**, 2026-11-16 (owner). Harena UI's plan, 1.1, carries the work.

## Context

Harena Term was published from `harena-hq/harena-term-font`: tags `v0.9.0` to `v1.0.3`, each with
a GitHub Release, and `@harena-hq/term-font` 1.0.0 to 1.0.3 on npm, whose published metadata names
that repository and cannot be changed. Harena UI was built in a repository of its own, never
pushed, which left the layout at release open until its first release (Harena UI's plan, 1.0).

## Decision

- **One repository, `harena-hq/fonts`**, made by renaming `harena-hq/harena-term-font`, so that
  GitHub keeps Term's issues, Releases and stars and redirects the old URL, which Term's npm and
  Debian metadata use. A repository is never created again under the old name, which would end the
  redirect.
- **Each family in a directory**: `term/` and `ui/`, each with its own `AGENTS.md`, `PLAN.md`,
  `docs/adr/`, build, gates, `SHA256SUMS`, licences and notices. The root holds only what both
  share: `README.md`, `AGENTS.md`, `.githooks/`, `.gitignore`, `.github/workflows/` and this
  directory, whose ADRs are cited as "fonts ADR NNNN".
- **No history rewritten.** Each family moved into its directory by a commit that only renames,
  and the two histories were joined by a merge. Every earlier commit and tag keeps its hash, and
  the joined `main` is a fast-forward of Term's published one. `main` requires linear history; the
  rule was lifted for that one push and restored.
- **Tags name the family, with a hyphen**: `term-v*` for a Term font release, `term-npm-v*` for a
  Term package-only release, `ui-v*` for a Harena UI release, whose version is its package's.
  Term's `v0.9.0` to `v1.0.3` stay as published.
- **One Latest.** GitHub marks one Release of a repository Latest. It stays Term's font release,
  which Term's READMEs send readers to for the fonts to install; Harena UI is delivered through
  npm, and its Releases are created with `--latest=false`.

## Rejected

- **`harena-hq/harena-fonts`.** It reads alone where the organization is not shown, in a fork or a
  local clone, but is longer. The working checkout is named `harena-fonts` instead.
- **A new repository**, which would leave Term's Releases, issues and URL behind.
- **`git filter-repo` into subdirectories**, which changes every hash, and with them the commits
  Term's published tags name.
- **Term at the root and UI in `ui/`**, which moves nothing of Term's but mixes its files with the
  shared ones and makes the two families' paths unlike.
- **A slash in tags** (`ui/v0.9.0`), which puts a directory into a Release's download path.

## Consequences

- `git log --follow` across the join mixes in the other family's commits for a path both had
  before the move (`PLAN.md`, `README.md`, `scripts/build.py`). From the family's own move commit,
  it follows one family: `git log --follow <move commit> -- ui/PLAN.md`.
- npm trusted publishing names the repository and the workflow file, and a rename does not carry
  it: each package's publisher is registered again for `harena-hq/fonts`, and Term's next release
  must name the new repository in its `package.json`, which provenance checks.
- A family's scripts run from its directory, as they did from its repository's root.
