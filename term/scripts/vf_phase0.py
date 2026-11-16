#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Phase-0 interpolatability gate for Harena Term VF.

This does not build a variable font.  It asks FontTools' own interpolatability
checker whether the two unhinted, cmap-reachable HarenaLatin endpoint masters
can participate in one ``wght`` designspace.  A non-empty problem set is a hard
stop: intermediate masters cannot repair incompatible endpoints.

Usage: python3 scripts/vf_phase0.py [--output build/vf-phase0.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from fontTools.ttLib import TTFont

from build import trim_base


ROOT = Path(__file__).resolve().parent.parent
UNHINTED = ROOT / "sources/iosevka-src/dist/HarenaLatin/TTF-Unhinted"
MASTERS = {
    "400": UNHINTED / "HarenaLatin-Regular.ttf",
    "700": UNHINTED / "HarenaLatin-Bold.ttf",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def trimmed_master(source: Path, destination: Path) -> dict[str, object]:
    font = TTFont(source)
    before = font["maxp"].numGlyphs
    dropped = trim_base(font)
    after = font["maxp"].numGlyphs
    font.save(destination)
    font.close()
    return {
        "source": str(source.relative_to(ROOT)),
        "sha256": sha256(source),
        "glyphs_before_trim": before,
        "glyphs_dropped": dropped,
        "glyphs_audited": after,
    }


def problem_counts(problems: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    counts = Counter(
        problem["type"]
        for glyph_problems in problems.values()
        for problem in glyph_problems
    )
    return dict(sorted(counts.items()))


def audit(output: Path) -> dict[str, object]:
    missing = [str(path.relative_to(ROOT)) for path in MASTERS.values()
               if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "missing unhinted HarenaLatin masters; run scripts/fetch_sources.sh: "
            + ", ".join(missing)
        )

    with tempfile.TemporaryDirectory(prefix="harena-vf-phase0-") as temp:
        tempdir = Path(temp)
        trimmed = {}
        paths = []
        for weight, source in MASTERS.items():
            destination = tempdir / f"HarenaLatin-{weight}.ttf"
            trimmed[weight] = trimmed_master(source, destination)
            paths.append(destination)

        raw_report = tempdir / "interpolatable.json"
        command = [
            sys.executable,
            "-m",
            "fontTools.varLib.interpolatable",
            "--json",
            "--output",
            str(raw_report),
            *(str(path) for path in paths),
        ]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        # FontTools returns 1 when it successfully found incompatibilities.
        if completed.returncode not in (0, 1):
            raise RuntimeError(
                "interpolatability checker failed\n"
                f"command: {' '.join(command)}\n"
                f"stdout: {completed.stdout}\n"
                f"stderr: {completed.stderr}"
            )
        problems = json.loads(raw_report.read_text()) if raw_report.exists() else {}

    report = {
        "phase": 0,
        "scope": "trimmed unhinted HarenaLatin 400/700 endpoints",
        "status": "pass" if not problems else "blocked",
        "stop_reason": (None if not problems else
                        "unresolved endpoint topology/interpolation problems"),
        "masters": trimmed,
        "problem_glyphs": len(problems),
        "problem_events": sum(len(items) for items in problems.values()),
        "problem_types": problem_counts(problems),
        "glyphs": problems,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "build/vf-phase0.json")
    args = parser.parse_args()

    try:
        report = audit(args.output.resolve())
    except (FileNotFoundError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 2

    print(f"Phase 0: {report['status']}")
    print(f"audited glyphs: {report['masters']['400']['glyphs_audited']}")
    print(f"problem glyphs: {report['problem_glyphs']}")
    print(f"problem events: {report['problem_events']}")
    for kind, count in report["problem_types"].items():
        print(f"  {kind}: {count}")
    print(f"report: {args.output}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
