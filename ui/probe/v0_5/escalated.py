# SPDX-License-Identifier: Apache-2.0
"""Read the escalation answers into .private/v0_5/escalated.json: {group: {kind, ...}}.

Usage: python probe/v0_5/escalated.py
"""
import collections
import glob
import json

from stages import ROOT

BADGES = {"add", "dismiss", "checkmark", "warning", "error", "lock", "prohibited", "clock", "heart", "charge"}


def main():
    base = ROOT / ".private/v0_5/C"
    rows = json.loads((base / "rows.json").read_text())
    out, bad = {}, []
    for f in sorted(glob.glob(str(base / "ans-*.txt"))):
        for line in open(f, encoding="utf-8"):
            parts = line.split()
            if not parts:
                continue
            try:
                row = rows[int(parts[0]) - 1]
                kind = parts[1]
                letter = lambda: row["cand"]["ABCDEFGH".index(parts[2])]
                if kind in ("PICK", "NEAR"):
                    out[row["group"]] = {"kind": kind, "stem": letter()}
                elif kind == "BADGE" and parts[3] in BADGES:
                    out[row["group"]] = {"kind": kind, "stem": letter(), "badge": parts[3]}
                elif kind == "TEXT":
                    out[row["group"]] = {"kind": kind, "text": " ".join(parts[2:-1]), "weight": parts[-1]}
                elif kind == "NONE":
                    out[row["group"]] = {"kind": kind}
                else:
                    bad.append(line.strip())
            except (IndexError, ValueError):
                bad.append(line.strip())
    (ROOT / ".private/v0_5/escalated.json").write_text(json.dumps(out, indent=0, ensure_ascii=False))
    print(len(out), "of", len(rows), collections.Counter(v["kind"] for v in out.values()).most_common(), "bad", bad[:10])


if __name__ == "__main__":
    main()
