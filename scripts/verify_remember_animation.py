#!/usr/bin/env python3
"""Verify that the ReMEMBER animation fits exact 20:9 viewports."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import websocket


ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = ((800, 360), (700, 315))


class QuietHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/__remember_wrapper_test__.html":
            body = b"""<!doctype html>
<html><head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/assets/css/custom.css">
<style>html,body{margin:0}.host{width:calc(100vw - 18px)}</style>
</head><body><div class="host">
<article class="publication-entry publication-entry--animation">
<div class="publication-entry__visual"><div class="publication-animation"></div></div>
</article></div></body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        return


class DevTools:
    def __init__(self, url: str) -> None:
        self.socket = websocket.create_connection(url, timeout=10)
        self.message_id = 0

    def close(self) -> None:
        self.socket.close()

    def call(self, method: str, params: dict[str, object] | None = None) -> dict:
        self.message_id += 1
        message_id = self.message_id
        self.socket.send(
            json.dumps({"id": message_id, "method": method, "params": params or {}})
        )
        while True:
            response = json.loads(self.socket.recv())
            if response.get("id") != message_id:
                continue
            if "error" in response:
                raise RuntimeError(f"{method} failed: {response['error']}")
            return response.get("result", {})


def find_chrome() -> str:
    candidates = (
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError("Chrome or Chromium is required for layout verification")


def wait_for_debugger(profile: Path) -> tuple[int, str]:
    port_file = profile / "DevToolsActivePort"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if port_file.is_file():
            lines = port_file.read_text(encoding="utf-8").splitlines()
            if len(lines) >= 2:
                return int(lines[0]), lines[1]
        time.sleep(0.05)
    raise RuntimeError("Chrome DevTools endpoint did not start")


def wait_for_page(devtools: DevTools, expected_url: str, selector: str) -> None:
    deadline = time.monotonic() + 10
    state: dict[str, object] = {}
    while time.monotonic() < deadline:
        result = devtools.call(
            "Runtime.evaluate",
            {
                "expression": (
                    "({ready: document.readyState, url: location.href, "
                    f"target: Boolean(document.querySelector({selector!r}))}})"
                ),
                "returnByValue": True,
            },
        )
        state = result["result"].get("value", {})
        if (
            state.get("ready") == "complete"
            and state.get("target")
            and state.get("url") == expected_url
        ):
            time.sleep(0.6)
            return
        time.sleep(0.05)
    raise RuntimeError(
        "animation page did not finish loading: "
        + json.dumps({"expected": expected_url, "actual": state})
    )


LAYOUT_EXPRESSION = r"""
(() => {
  const tolerance = 1;
  const violations = [];
  const selectors = [
    "html", "body", "#rm-stage", "#rm-header", "#rm-chat",
    "#rm-gaps", "#rm-archive", "#rm-summary"
  ];
  const rectFor = (element) => {
    const rect = element.getBoundingClientRect();
    return {
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
      left: rect.left,
      width: rect.width,
      height: rect.height,
      clientWidth: element.clientWidth,
      clientHeight: element.clientHeight,
      scrollWidth: element.scrollWidth,
      scrollHeight: element.scrollHeight
    };
  };
  const metrics = Object.fromEntries(selectors.map((selector) => {
    const element = document.querySelector(selector);
    return [selector, rectFor(element)];
  }));

  for (const selector of selectors) {
    const metric = metrics[selector];
    if (metric.left < -tolerance || metric.top < -tolerance ||
        metric.right > innerWidth + tolerance ||
        metric.bottom > innerHeight + tolerance) {
      violations.push(`${selector} exceeds viewport`);
    }
    if (metric.scrollWidth > metric.clientWidth + tolerance ||
        metric.scrollHeight > metric.clientHeight + tolerance) {
      violations.push(`${selector} clips scrollable content`);
    }
  }

  const horizontalPairs = [
    ["#rm-chat", "#rm-gaps"],
    ["#rm-gaps", "#rm-archive"],
    ["#rm-chat", "#rm-summary"]
  ];
  for (const [leftSelector, rightSelector] of horizontalPairs) {
    if (metrics[leftSelector].right > metrics[rightSelector].left + tolerance) {
      violations.push(`${leftSelector} overlaps ${rightSelector}`);
    }
  }
  for (const upperSelector of ["#rm-gaps", "#rm-archive"]) {
    if (metrics[upperSelector].bottom > metrics["#rm-summary"].top + tolerance) {
      violations.push(`${upperSelector} overlaps #rm-summary`);
    }
  }

  const visibleContent = document.querySelectorAll(
    ".rm-msg, .rm-bubble, .rm-gap-slot, .rm-slot-label, .rm-slot-fill, " +
    ".rm-evidence-card, .rm-summary-text, .rm-fact"
  );
  for (const element of visibleContent) {
    const style = getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" ||
        Number.parseFloat(style.opacity) < 0.05) {
      continue;
    }
    const panel = element.closest("#rm-chat, #rm-gaps, #rm-archive, #rm-summary");
    const contentRect = element.getBoundingClientRect();
    const panelRect = panel.getBoundingClientRect();
    if (element.clientWidth && element.scrollWidth > element.clientWidth + tolerance) {
      violations.push(`${element.className} clips horizontal content`);
    }
    if (element.clientHeight && element.scrollHeight > element.clientHeight + tolerance) {
      violations.push(`${element.className} clips vertical content`);
    }
    if (element.matches(".rm-bubble")) {
      const lineHeight = Number.parseFloat(style.lineHeight);
      const lineCount = contentRect.height / lineHeight;
      if (lineCount > 3.1) {
        violations.push(`${element.textContent.trim()} wraps to ${lineCount.toFixed(1)} lines`);
      }
    }
    if (contentRect.left < panelRect.left - tolerance ||
        contentRect.top < panelRect.top - tolerance ||
        contentRect.right > panelRect.right + tolerance ||
        contentRect.bottom > panelRect.bottom + tolerance) {
      const identity = element.dataset.gap
        ? `${element.className}[data-gap=${element.dataset.gap}]`
        : element.className;
      violations.push(`${identity} is clipped by ${panel.id}`);
    }
  }

  return {
    viewport: {width: innerWidth, height: innerHeight},
    phase: document.querySelector("#rm-stage").dataset.phase,
    metrics,
    violations: [...new Set(violations)]
  };
})()
"""


def verify_viewport(devtools: DevTools, url: str, width: int, height: int) -> None:
    devtools.call(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
    )
    devtools.call("Page.navigate", {"url": url})
    wait_for_page(devtools, url, "#rm-stage")
    evaluation = devtools.call(
        "Runtime.evaluate",
        {"expression": LAYOUT_EXPRESSION, "returnByValue": True},
    )
    if "exceptionDetails" in evaluation:
        raise RuntimeError(json.dumps(evaluation["exceptionDetails"], indent=2))
    remote_result = evaluation["result"]
    if "value" not in remote_result:
        raise RuntimeError(json.dumps(remote_result, indent=2))
    result = remote_result["value"]
    assert result["viewport"] == {"width": width, "height": height}, result
    assert result["phase"] in {"summary", "hold"}, result
    assert not result["violations"], json.dumps(result, indent=2)


def verify_publication_wrapper(devtools: DevTools, url: str) -> None:
    width, height = 800, 360
    devtools.call(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
    )
    devtools.call("Page.navigate", {"url": url})
    wait_for_page(devtools, url, ".publication-animation")
    result = devtools.call(
        "Runtime.evaluate",
        {
            "expression": """
(() => {
  const element = document.querySelector('.publication-animation');
  const visual = document.querySelector('.publication-entry__visual');
  return {
    width: element.clientWidth,
    height: element.clientHeight,
    ratio: element.clientHeight / element.clientWidth,
    visualWidth: visual.clientWidth
  };
})()
""",
            "returnByValue": True,
        },
    )["result"]["value"]
    expected_ratio = 9 / 20
    assert result["visualWidth"] >= 700, result
    assert abs(result["ratio"] - expected_ratio) < 0.01, result


def main() -> None:
    handler = lambda *args, **kwargs: QuietHandler(  # noqa: E731
        *args, directory=str(ROOT), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    with tempfile.TemporaryDirectory(prefix="remember-animation-") as profile_dir:
        profile = Path(profile_dir)
        chrome = subprocess.Popen(
            [
                find_chrome(),
                "--headless=new",
                "--disable-gpu",
                "--disable-extensions",
                "--no-sandbox",
                "--remote-allow-origins=*",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        devtools = None
        try:
            port, _ = wait_for_debugger(profile)
            pages = json.loads(
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/list", timeout=5
                ).read()
            )
            page = next(
                item
                for item in pages
                if item.get("type") == "page" and item.get("url") == "about:blank"
            )
            page_url = page["webSocketDebuggerUrl"]
            devtools = DevTools(page_url)
            devtools.call("Page.enable")
            devtools.call("Runtime.enable")
            animation_url = (
                f"http://127.0.0.1:{server.server_port}"
                "/static/uploads/research/remember-loop.html#t=20000"
            )
            for width, height in VIEWPORTS:
                verify_viewport(devtools, animation_url, width, height)
                screenshot_path = os.environ.get("REMEMBER_SCREENSHOT")
                if screenshot_path and (width, height) == VIEWPORTS[0]:
                    screenshot = devtools.call(
                        "Page.captureScreenshot",
                        {"format": "png", "captureBeyondViewport": False},
                    )
                    Path(screenshot_path).write_bytes(
                        base64.b64decode(screenshot["data"])
                    )
            wrapper_url = (
                f"http://127.0.0.1:{server.server_port}"
                "/__remember_wrapper_test__.html"
            )
            verify_publication_wrapper(devtools, wrapper_url)
        finally:
            if devtools is not None:
                devtools.close()
            chrome.terminate()
            try:
                chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome.kill()
            server.shutdown()
            server.server_close()

    print("remember animation verification passed")


if __name__ == "__main__":
    main()
