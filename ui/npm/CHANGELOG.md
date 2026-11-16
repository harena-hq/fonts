# Changelog

Notable changes to the `@harena-hq/ui-font` npm package. The package carries
three families, each with its own font version (`harena.fontVersions` in
`package.json`); the package version is what a release of it is tagged with
(`ui-v*`).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this package uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] — unreleased

### Added

- The first release: Harena UI 0.3.0, Harena UI J 0.8.0 and Harena UI Icons
  0.5.2 as WOFF2, split by script and frequency so a page fetches only the
  files its text uses, with `index.css`, `ui.css`, `j.css` and `icons.css`.
  Named after Segoe in a font stack, a page lays out as under Segoe on Windows,
  and in Safari, WebKitGTK, Chrome and Firefox on macOS and Linux as in Edge on
  Windows, but for what
  [`ui/docs/engines.md`](https://github.com/harena-hq/fonts/blob/main/ui/docs/engines.md) lists.
