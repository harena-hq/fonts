# SPDX-License-Identifier: Apache-2.0
"""Compare two runs of picks on the same rows. Writes .private/v0_5/picks.json (agreed) and
.private/v0_5/open.json (no match in either run, or the runs differ).

Usage: python probe/v0_5/reconcile.py A B
"""
import glob
import json
import sys

from stages import ROOT


def read(run):
    base = ROOT / ".private/v0_5" / run
    rows = json.loads((base / "rows.json").read_text())
    out = {}
    for f in glob.glob(str(base / "ans-*.txt")):
        for line in open(f):
            if line.strip():
                n, answer = line.split()
                row = rows[int(n) - 1]
                out[row["group"]] = None if answer == "NONE" else row["cand"]["ABCDEFGH".index(answer)]
    assert len(out) == len(rows), (run, len(out), len(rows))
    return out


def main():
    a, b = read(sys.argv[1]), read(sys.argv[2])
    agreed = {g: a[g] for g in a if a[g] and a[g] == b[g]}
    both_none = [g for g in a if not a[g] and not b[g]]
    one_none = [g for g in a if bool(a[g]) != bool(b[g])]
    differ = [g for g in a if a[g] and b[g] and a[g] != b[g]]
    base = ROOT / ".private/v0_5"
    (base / "picks.json").write_text(json.dumps(agreed, indent=0))
    (base / "open.json").write_text(json.dumps({"both_none": both_none, "one_none": one_none, "differ": differ,
                                                "a": a, "b": b}, indent=0))
    print("agreed", len(agreed), "both none", len(both_none), "one none", len(one_none), "differ", len(differ))


if __name__ == "__main__":
    main()
