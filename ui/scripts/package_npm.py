#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Jeeyong Um
"""Assemble the npm package from the tracked metadata in npm/ and the ignored WOFF2 output, as
Harena Term's package_npm.py does: build/npm-package/, ready for `npm pack`.

It refuses a package whose fonts do not match SHA256SUMS-Web, whose stylesheets are not what
build_css.py writes, or whose harena.fontVersions are not the fonts' own.

Usage: python scripts/package_npm.py [--out build/npm-package]
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_css  # noqa: E402
from build import ROOT  # noqa: E402
from build_web import WEB  # noqa: E402

NPM = ROOT / "npm"
LICENSES = {"Apache-2.0.txt": ROOT / "LICENSE",
            "Open-Sans-OFL-1.1.txt": ROOT / "docs/LICENSE-Open-Sans.txt",
            "Pretendard-JP-OFL-1.1.txt": ROOT / "docs/LICENSE-Pretendard-JP.txt",
            "Fluent-UI-System-Icons-MIT.txt": ROOT / "docs/LICENSE-Fluent-UI-System-Icons.txt"}
FAMILIES = {"Harena UI": "HarenaUI-", "Harena UI J": "HarenaUIJ-", "Harena UI Icons": "HarenaUIIcons-"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def problems(package):
    out = []
    listed = {}
    for line in (ROOT / "SHA256SUMS-Web").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        listed[Path(name).name] = digest
    for name, digest in listed.items():
        if not (WEB / name).is_file() or sha256(WEB / name) != digest:
            out.append(f"{name} does not match SHA256SUMS-Web")
    stale = [n for n, text in build_css.stylesheets().items() if (NPM / n).read_text() != text]
    if stale:
        out.append(f"stylesheets differ from build_css.py's: {' '.join(stale)}")
    versions = package.get("harena", {}).get("fontVersions", {})
    for family, prefix in FAMILIES.items():
        names = {TTFont(WEB / n, lazy=True)["name"].getDebugName(5) for n in listed if n.startswith(prefix)}
        if names != {f"Version {versions.get(family)}"}:
            out.append(f"{family}: harena.fontVersions says {versions.get(family)}, the fonts {sorted(names)}")
    return out, sorted(listed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "build/npm-package")
    out = parser.parse_args().out.resolve()
    package = json.loads((NPM / "package.json").read_text())
    issues, fonts = problems(package)
    if issues:
        print(*issues, sep="\n", file=sys.stderr)
        return 1
    # It is deleted and rewritten: only a directory under build/ may be.
    if (ROOT / "build") not in out.parents:
        print(f"refusing output outside build/: {out}", file=sys.stderr)
        return 1
    if out.exists():
        shutil.rmtree(out)
    (out / "fonts").mkdir(parents=True)
    for item in NPM.iterdir():
        shutil.copy2(item, out / item.name)
    for name in fonts:
        shutil.copy2(WEB / name, out / "fonts" / name)
    shutil.copy2(ROOT / "OFL.txt", out / "OFL.txt")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", out / "THIRD_PARTY_NOTICES.md")
    (out / "licenses").mkdir()
    for name, source in LICENSES.items():
        shutil.copy2(source, out / "licenses" / name)
    # Every url() a stylesheet names is in the package.
    named = {m for css in out.glob("*.css") for m in re.findall(r'url\("\./fonts/([^"]+)"\)', css.read_text())}
    if named != set(fonts):
        print(f"stylesheets name {len(named - set(fonts))} missing and leave {len(set(fonts) - named)} unused fonts",
              file=sys.stderr)
        return 1
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"assembled {package['name']}@{package['version']} in {out} ({size / 1e6:.1f} MB, {len(fonts)} fonts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
