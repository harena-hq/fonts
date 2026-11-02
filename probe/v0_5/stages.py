# SPDX-License-Identifier: Apache-2.0
"""What each glyph group's stand-in comes from before any model looks; shared by the table steps.

Usage: python probe/v0_5/stages.py   prints the count per stage, writes build/v0_5/stages.json
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# winui-svelte's scripts/icons/fallback.mjs: its rows carry over. Needed only to re-derive the table.
SEED = Path(os.environ.get("HARENA_ICON_SEED", "fallback.mjs"))


def stem(name):
    return re.sub(r"_\d+_(regular|filled)$", "", name.replace("ic_fluent_", ""))


def load():
    points = json.loads((ROOT / "data/v0_5/segoe-icons.json").read_text())["points"]
    names = json.loads((ROOT / "data/v0_5/segoe-names.json").read_text())["names"]
    rank = json.loads((ROOT / "build/v0_5/rank.json").read_text())
    group_of = {r[0]: r[1] for r in points}
    rep, gname, blank = {}, {}, set()
    for r in points:
        rep.setdefault(r[1], r[0])
        if r[3] is None:
            blank.add(r[1])
    for p, n in sorted(names.items()):
        if p in group_of:
            gname.setdefault(group_of[p], n)
    mirror = {group_of[a]: group_of[b] for a, b, c in rank["pairs"] if c is not None and c >= 0.97 and group_of[a] != group_of[b]}
    mapping = {}
    for m in json.loads((ROOT / "sources/symboliconmanager/SegoeFluent.json").read_text()):
        if m["Source"]["IconSet"].startswith("Fluent") and not m["IsPlaceholder"]:
            mapping.setdefault(group_of[m["Destination"]["UnicodePoint"].upper()], stem(m["Source"]["Name"]))
    return rep, gname, blank, mirror, mapping, rank["nearest"], group_of


def nearest_stems(near, point, k):
    out = []
    for name, _ in near.get(point, []):
        s = stem(name)
        if s not in out:
            out.append(s)
        if len(out) == k:
            break
    return out


def main():
    rep, gname, blank, mirror, mapping, near, group_of = load()
    seed = {}
    text = SEED.read_text()
    for p, f in re.findall(r"point: '([0-9A-F]+)',\s*segoe: '[^']*',\s*fluent: '([a-z0-9_]+)'", text):
        if p in group_of:
            seed.setdefault(group_of[p], f)
    stages = {}
    for g, p in rep.items():
        if g in blank:
            s = {"stage": "blank"}
        elif g in seed:
            s = {"stage": "seed", "fluent": seed[g]}
        elif g in mirror and mirror[g] not in mirror:
            s = {"stage": "mirror", "of": mirror[g]}
        elif g in mapping and mapping[g] in nearest_stems(near, p, 5):
            s = {"stage": "agreed", "stem": mapping[g]}
        else:
            s = {"stage": "pick"}
        stages[g] = {"point": p, "name": gname.get(g), **s}
    (ROOT / "build/v0_5/stages.json").write_text(json.dumps(stages, indent=0))
    count = {}
    for s in stages.values():
        count[s["stage"]] = count.get(s["stage"], 0) + 1
    print(count, "total", len(stages))
    picks = sorted(s["name"] for s in stages.values() if s["stage"] == "pick" and s["name"])
    vocab = sorted({w for n in json.loads((ROOT / "build/v0_5/fluent.json").read_text()).values() for w in n["s"].split("_") if not w.isdigit()})
    (ROOT / "build/v0_5/vocab.txt").write_text(" ".join(vocab) + "\n")
    for i in range(0, len(picks), 300):
        (ROOT / f"build/v0_5/names-{i // 300 + 1}.txt").write_text("\n".join(picks[i:i + 300]) + "\n")
    print(len(picks), "named picks in", (len(picks) + 299) // 300, "files")


if __name__ == "__main__":
    main()
