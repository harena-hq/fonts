# SPDX-License-Identifier: Apache-2.0
"""Run probe/v1_0/measure.js in a page of one engine, through the protocol that engine speaks.

- CDP (Edge on Windows, the reference): probe/cdp.mjs, as through v0.7; its one capability,
  `deviceScaleFactor`, lays pages out as on a display at that scale.
- W3C WebDriver (safaridriver, WebKitWebDriver, chromedriver, geckodriver): one session per engine,
  each run on a freshly loaded page.

An engine is named by a spec: "cdp=<http-base>" or "webdriver=<http-base>" with its capabilities.
"""
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / "probe/v1_0/measure.js").read_text()
WORK = ROOT / "build/v1_0"


class Cdp:
    def __init__(self, base, capabilities):
        unknown = set(capabilities) - {"deviceScaleFactor"}
        if unknown:
            raise ValueError(f"cdp takes deviceScaleFactor only, not {sorted(unknown)}")
        self.base = base
        self.scale = capabilities.get("deviceScaleFactor")

    def identity(self):
        v = json.loads(urllib.request.urlopen(f"{self.base}/json/version", timeout=30).read())
        return {"protocol": "cdp", "browser": v["Browser"]} | ({"deviceScaleFactor": self.scale} if self.scale else {})

    def run(self, page, config, seconds):
        WORK.mkdir(parents=True, exist_ok=True)
        expr = WORK / "expr.js"
        expr.write_text(f"const CONFIG = {json.dumps(config, ensure_ascii=False)};\n" + SCRIPT)
        res = subprocess.run(["node", str(ROOT / "probe/cdp.mjs"), self.base, page, str(expr), str(seconds)]
                             + ([str(self.scale)] if self.scale else []),
                             capture_output=True, text=True, timeout=seconds + 60)
        if res.returncode:
            raise RuntimeError(f"cdp: {res.stderr.strip()[:2000]}")
        return json.loads(res.stdout)

    def close(self):
        pass


class WebDriver:
    def __init__(self, base, capabilities):
        self.base = base
        value = self._call("POST", "/session", {"capabilities": {"alwaysMatch": capabilities}})
        self.session = f"/session/{value['sessionId']}"
        self.capabilities = value["capabilities"]

    def _call(self, method, path, body=None, seconds=120):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=seconds) as res:
                return json.loads(res.read())["value"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"webdriver {method} {path}: {e.read().decode()[:2000]}") from None

    def identity(self):
        c = self.capabilities
        return {"protocol": "webdriver", "browser": f"{c.get('browserName')} {c.get('browserVersion')}",
                "platform": f"{c.get('platformName')} {c.get('platformVersion') or c.get('safari:platformVersion') or ''}".strip()}

    def run(self, page, config, seconds):
        self._call("POST", f"{self.session}/timeouts", {"script": seconds * 1000, "pageLoad": 120000})
        self._call("POST", f"{self.session}/url", {"url": page})
        script = (f"const CONFIG = {json.dumps(config, ensure_ascii=False)};\n"
                  "const done = arguments[arguments.length - 1];\n"
                  f"Promise.resolve(\n{SCRIPT}\n).then((v) => done({{ok: v}}), (e) => done({{error: String(e && e.stack || e)}}));")
        value = self._call("POST", f"{self.session}/execute/async", {"script": script, "args": []}, seconds + 60)
        if "error" in value:
            raise RuntimeError(f"script: {value['error'][:2000]}")
        return value["ok"]

    def close(self):
        try:
            self._call("DELETE", self.session)
        except Exception:  # noqa: BLE001 - the session may already be gone
            pass


def connect(spec, capabilities=None):
    kind, _, base = spec.partition("=")
    if kind == "cdp":
        return Cdp(base, capabilities or {})
    if kind == "webdriver":
        return WebDriver(base, capabilities or {})
    raise ValueError(f"engine spec {spec!r}: expected cdp=<url> or webdriver=<url>")
