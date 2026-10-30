# SPDX-License-Identifier: Apache-2.0
"""Measure v0's tables on the reference browser and write them under data/v0/.

Only what needs the browser is measured here: Segoe UI Variable, which exists
only on the reference machine, and the stems of every font, which are read from
pixels. Candidate fonts' advances and outlines are read offline by analyze.py;
method-check.json is the evidence that the browser and fontTools agree.

Passes:

1. Stems: the vertical stem of `l` and `I` (stems.js) for every Segoe instance and
   for each candidate across its weight range. A candidate is compared with each
   Segoe instance at the weight whose stems match, interpolated and rounded.
2. Segoe: advances, kerning and strings (measure.js) and ink boxes from pixels
   (ink.js), for the 12 named instances.
3. Method check: the same two passes on Pretendard JP at 400, whose exact answer
   fontTools gives.

Units are px at a 1000 px font size, i.e. per-mille of the em. Glyph rows are
[advance]; ink rows are [left, right, top, bottom], y up. Kerning is width(ab) -
width(a) - width(b), kept where it is at least 0.05. String rows are [kerned,
unkerned].

4. opsz check (opsz.js): whether font size, font-optical-sizing or an explicit
   opsz setting moves a named instance's widths. `--opsz-only` runs just this.

Usage: python probe/v0/run.py <cdp-http-base> <page-base-url> <provenance.json> [--opsz-only]

<page-base-url> must serve the repository root, since probe/page.html loads
../sources/. <provenance.json> describes the machine: {"measured", "os",
"browser", "segoe_ui_variable": {"file", "version", "sha256"}}.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = [350, 400, 600, 700]
SEGOE = ["Segoe UI Variable Small", "Segoe UI Variable Text", "Segoe UI Variable Display"]
CANDIDATES = {
    "Pretendard JP Probe": range(45, 931, 5),
    "Open Sans Probe": range(300, 801, 5),
    "Noto Sans Probe": range(100, 901, 5),
    "Selawik Probe": [300, 350, 400, 600, 700],
}

GLYPHS = list(range(0x20, 0x7F)) + list(range(0xA0, 0x100))
STRINGS = json.loads((ROOT / "probe/v0/strings.json").read_text())
PAIRS = sorted(set(map(ord, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
                            ".,:;-'\"()/!?&"))
               | {ord(c) for g in STRINGS.values() for s in g for c in s})


def evaluate(cdp, page, script, config):
    expr = f"const CONFIG = {json.dumps(config)};\n" + (ROOT / "probe/v0" / script).read_text()
    tmp = ROOT / "build/v0-expr.js"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(expr)
    res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), cdp, page, str(tmp), "900"],
                         capture_output=True, text=True, timeout=960, check=True)
    return json.loads(res.stdout)


def matched_weights(stems):
    out = {}
    for cand in CANDIDATES:
        scan = sorted((int(k.split("|")[1]), v) for k, v in stems.items() if k.startswith(cand + "|"))
        for key, v in stems.items():
            if not key.startswith("Segoe"):
                continue
            ws = []
            for ch in "lI":
                for (a, va), (b, vb) in zip(scan, scan[1:]):
                    if va[ch] <= v[ch] <= vb[ch] and vb[ch] > va[ch]:
                        ws.append(a + (b - a) * (v[ch] - va[ch]) / (vb[ch] - va[ch]))
                        break
            out.setdefault(cand, {})[key] = round(sum(ws) / len(ws)) if len(ws) == 2 else None
    return out


def write(name, provenance, method, data):
    doc = {"provenance": {**provenance, "method": method}, "unit": "px at 1000 px font size", **data}
    (ROOT / "data/v0" / f"{name}.json").write_text(json.dumps(doc, indent=0, sort_keys=True) + "\n")


def measure_full(cdp, page, fams):
    cfg = {"glyphs": GLYPHS, "pairs": PAIRS, "strings": STRINGS, "families": fams}
    metrics = evaluate(cdp, page, "measure.js", cfg)
    ink = evaluate(cdp, page, "ink.js", {"glyphs": GLYPHS, "families": fams})
    out = {}
    for key, m in metrics.items():
        out[key] = {"advance": {cp: row[0] for cp, row in m["glyphs"].items()},
                    "ink": ink[key], "kern": m["kern"], "strings": m["strings"]}
    return out


def opsz_check(cdp, page, provenance):
    fams = SEGOE + ["Segoe UI Variable", "Segoe UI", "NoSuchFamily"]
    widths = evaluate(cdp, page, "opsz.js", {"families": fams, "weights": WEIGHTS,
                                             "text": "Hamburgefonstiv 0123456789"})
    write("opsz-check", provenance, "canvas measureText and DOM span width, per 1000 px of size",
          {"widths": widths})


def main():
    cdp, base, prov = sys.argv[1:4]
    if "--opsz-only" in sys.argv:
        provenance = json.loads(Path(prov).read_text())
        opsz_check(cdp, f"{base}/probe/page.html", provenance)
        return
    provenance = json.loads(Path(prov).read_text())
    (ROOT / "data/v0").mkdir(parents=True, exist_ok=True)
    page = f"{base}/probe/page.html"

    fams = [[f, w] for f in SEGOE for w in WEIGHTS]
    fams += [[c, w] for c, ws in CANDIDATES.items() for w in ws]
    stems = evaluate(cdp, page, "stems.js", {"families": fams, "chars": "lI"})
    matched = matched_weights(stems)
    write("stems", provenance, "pixel coverage along one row 250 px above the baseline, 1000 px",
          {"stems": stems, "matched_wght": matched})
    unmatched = [(c, k) for c, m in matched.items() for k, w in m.items() if w is None]
    print("no stem match:", unmatched or "none")

    method = ("advances, kerning, strings: canvas measureText at 1000 px, fontKerning normal; "
              "ink: pixel edges at 1000 px")
    seg = measure_full(cdp, page, [[f, w] for f in SEGOE for w in WEIGHTS])
    write("segoe-ui-variable", provenance, method, {"instances": seg})
    chk = measure_full(cdp, page, [["Pretendard JP Probe", 400]])
    write("method-check", provenance, method, {"instances": chk})
    opsz_check(cdp, page, provenance)
    print(f"segoe-ui-variable {len(seg)} instances; method-check {len(chk)}")


if __name__ == "__main__":
    main()
