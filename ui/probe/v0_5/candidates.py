# SPDX-License-Identifier: Apache-2.0
"""Offer at most eight Fluent names per glyph group: the mapping's, the nearest by raster, and the
nearest in words to what the text pass called it (build/v0_5/kw-*.json). Writes build/v0_5/candidates.json.

Usage: python probe/v0_5/candidates.py
"""
import glob
import json
from pathlib import Path

from stages import ROOT, load, nearest_stems, stem

LIMIT = 8


def main():
    rep, gname, blank, mirror, mapping, near, group_of = load()
    keywords = {}
    for f in glob.glob(str(ROOT / "build/v0_5/kw-*.json")):
        keywords.update(json.loads(Path(f).read_text()))
    stems = {v["s"] for v in json.loads((ROOT / "build/v0_5/fluent.json").read_text()).values()}
    words = {s: set(s.split("_")) for s in stems}

    def by_words(phrases, k=4):
        out = [p for p in phrases if p in stems]
        scored = {}
        for rank, p in enumerate(phrases):
            want = set(p.split("_"))
            for s, have in words.items():
                hit = len(want & have)
                if hit:
                    score = hit / len(want | have) - rank * 0.01
                    scored[s] = max(scored.get(s, 0), score)
        for s, _ in sorted(scored.items(), key=lambda kv: (-kv[1], kv[0])):
            if s not in out:
                out.append(s)
        return out[:k]

    table = {}
    for g, p in rep.items():
        offered = []
        if g in mapping and mapping[g] in stems:
            offered.append(mapping[g])
        raster = nearest_stems(near, p, LIMIT)
        worded = by_words(keywords.get(gname.get(g), []))
        for s in raster[:3] + worded + raster[3:]:
            if s not in offered and len(offered) < LIMIT:
                offered.append(s)
        table[g] = offered
    (ROOT / "build/v0_5/candidates.json").write_text(json.dumps(table))


if __name__ == "__main__":
    main()
