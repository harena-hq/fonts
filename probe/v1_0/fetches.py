# SPDX-License-Identifier: Apache-2.0
"""1.0 item 5: the font files each of v0.6's nine pages fetches in one engine, seen at the server.

Resource Timing lists no font files in WebKitGTK, so what a page fetched is read from the file
server's request log (probe/v1_0/serve.py --log) instead, and the engine's Resource Timing is kept
beside it where it has one. Each page is loaded as page.html?fetch=<n>-<nonce>; what the log holds
after that request and before the next page's is that page's. The server must serve this engine
alone while it runs, which the nonce checks only in part: start one for the run. Each page has a
session of its own: Firefox keeps a font it fetched for an earlier page, whatever the cache headers.

Usage: python probe/v1_0/fetches.py <engine> <base-url> <server-log> <out.json> --platform TEXT [--caps JSON]
"""
import argparse
import json
import secrets
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "probe/v1_0")]
from collect import artifacts, digest, fetch_cases, inputs  # noqa: E402
from drive import connect  # noqa: E402

FONTS = "/build/npm-package/fonts/"


def served(lines, mark):
    """The fonts the log's lines after the page request `mark` hold, or None if it is not there."""
    paths = [(json.loads(line)["path"], json.loads(line)["status"]) for line in lines]
    starts = [i for i, (p, _) in enumerate(paths) if urlsplit(p).path == "/probe/page.html"]
    mine = [i for i in starts if urlsplit(paths[i][0]).query == f"fetch={mark}"]
    if len(starts) != 1 or len(mine) != 1:
        return None  # another page loaded from this server meanwhile: its fetches cannot be told apart
    after = paths[mine[0] + 1:]
    return sorted({p[len(FONTS):] for p, status in after if p.startswith(FONTS) and p.endswith(".woff2")
                   and status == 200}), [p for p, status in after
                                                    if status != 200 and p.startswith(("/build/", "/dist/"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine")
    ap.add_argument("base")
    ap.add_argument("log")
    ap.add_argument("out")
    ap.add_argument("--caps", default="{}")
    ap.add_argument("--platform", required=True)
    args = ap.parse_args()

    inp = inputs()
    cases = fetch_cases()
    log = Path(args.log)
    caps = json.loads(args.caps)
    pkg = f"{args.base}/build/npm-package"
    sheets = [f"{pkg}/ui.css", f"{pkg}/j.css", f"{pkg}/icons.css"]
    result = {"inputs": {"fetch_cases": digest(cases), "artifacts": artifacts(inp)}, "served": {}, "timing": {},
              "failed": {}}
    page = f"{args.base}/probe/page.html"
    for n, (name, font_stack, lang, text, _) in enumerate(cases):
        engine = connect(args.engine, caps)
        try:
            identity = engine.identity() | {"page": engine.run(page, {"mode": "env"}, 120), "guest": args.platform}
            if result.setdefault("engine", identity) != identity:
                sys.exit(f"{name}: another engine, {identity}")
            mark = f"{n}-{secrets.token_hex(4)}"
            config = {"sheets": sheets, "mode": "fetch", "font": f"400 20px {font_stack}", "lang": lang, "text": text}
            start = log.stat().st_size
            timing = engine.run(f"{page}?fetch={mark}", config, 600)
        finally:
            engine.close()
        with log.open("rb") as f:
            f.seek(start)
            lines = f.read().decode().splitlines()
        seen = served(lines, mark)
        if seen is None:
            sys.exit(f"{name}: the log does not hold this page's request alone; is the server this engine's?")
        result["served"][name], failed = seen
        if failed:
            result["failed"][name] = failed
        result["timing"][name] = sorted(timing)
        print(name, result["served"][name], flush=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
