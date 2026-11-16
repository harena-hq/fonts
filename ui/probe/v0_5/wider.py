# SPDX-License-Identifier: Apache-2.0
"""For rows the picks left open: the two runs' answers, then names not yet offered, in words and by
raster. Writes build/v0_5/candidates2.json and build/v0_5/open-rows.json.

Usage: python probe/v0_5/wider.py
"""
import json

from candidates import LIMIT
from stages import ROOT, load, nearest_stems


def main():
    rep, gname, blank, mirror, mapping, near, group_of = load()
    state = json.loads((ROOT / ".private/v0_5/open.json").read_text())
    first = json.loads((ROOT / "build/v0_5/candidates.json").read_text())
    groups = state["both_none"] + state["one_none"] + state["differ"]
    out = {}
    for g in groups:
        offered = [x for x in (state["a"][g], state["b"][g]) if x]
        offered = list(dict.fromkeys(offered))
        for s in nearest_stems(near, rep[int(g)], 24):
            if s not in first[g] and s not in offered and len(offered) < LIMIT:
                offered.append(s)
        out[g] = offered
    (ROOT / "build/v0_5/candidates2.json").write_text(json.dumps(out))
    (ROOT / "build/v0_5/open-rows.json").write_text(json.dumps(groups))
    print(len(groups), "open rows")


if __name__ == "__main__":
    main()
