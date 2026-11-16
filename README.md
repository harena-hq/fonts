# Harena fonts

The typefaces of [Harena](https://github.com/harena-hq), each in a directory of its own with its
own build, gates, decisions and releases.

| directory | typeface | for | releases |
|---|---|---|---|
| [`term/`](term/) | **Harena Term** | terminals: Korean, Japanese and English on a strict 1:2 cell grid | tags `term-v*`, npm `@harena-hq/term-font` |
| [`ui/`](ui/) | **Harena UI**, **Harena UI J**, **Harena UI Icons** | interfaces: Segoe UI Variable's and Segoe Fluent Icons' geometry where they are not installed | tags `ui-v*`, npm `@harena-hq/ui-font` |

Each directory's `README.md` says how to build and use its fonts, its `PLAN.md` what it is built
to and why, and its `docs/adr/` the decisions. [`docs/adr/`](docs/adr/) here holds the decisions
about the repository itself.

Harena Term's releases before it moved here are tagged `v0.9.0` to `v1.0.3`.

## Licence

The fonts are under the SIL Open Font License 1.1 and the scripts under the Apache License 2.0;
each directory carries its own `OFL.txt`, `LICENSE` and notices for the sources it builds from.
