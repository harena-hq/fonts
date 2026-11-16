# SPDX-License-Identifier: Apache-2.0
"""Serve the probe's files from this checkout to the engines (PLAN.md, 1.0).

Only what a probe page loads is served: probe/, the package (build/npm-package) and the TTFs (dist/);
nothing else in the checkout. Every response says `Cache-Control: no-store`, so that an engine never
lays out a package it fetched before the one being measured.

With --log, each request answered is appended to FILE as a JSON line (path and status), as it is
answered: what probe/v1_0/fetches.py reads to see which files a page fetched, in an engine whose
Resource Timing does not list them.

Usage: python probe/v1_0/serve.py <bind-address> <port> [--log FILE]
"""
import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SERVED = ("probe/", "build/npm-package/", "dist/")


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = unquote(urlsplit(self.path).path).lstrip("/")
        resolved = (ROOT / path).resolve()
        # a file only: a directory would serve an index (or a listing) this check never saw
        if (not path.startswith(SERVED) or ".." in Path(path).parts or not resolved.is_file()
                or not any(resolved.is_relative_to(ROOT / p) for p in SERVED)):
            self.send_error(404)
            return None
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    log = None
    lock = threading.Lock()

    def log_request(self, code="-", size="-"):
        super().log_request(code, size)
        if self.log:
            with self.lock:
                self.log.write(json.dumps({"path": self.path, "status": getattr(code, "value", code)}) + "\n")
                self.log.flush()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")


def main():
    host, port = sys.argv[1], int(sys.argv[2])
    if sys.argv[3:4] == ["--log"]:
        Handler.log = open(sys.argv[4], "a", encoding="utf-8")
    ThreadingHTTPServer((host, port), partial(Handler, directory=str(ROOT))).serve_forever()


if __name__ == "__main__":
    main()
