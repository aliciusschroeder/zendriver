"""Regression tests for group R35 (headless UA override applied lazily). Needs real chromium."""

import asyncio
import http.server
import shutil
import threading
import time

import pytest

import zendriver as zd

print("\nzendriver imported from", zd.__file__)

pytestmark = pytest.mark.skipif(shutil.which("chromium") is None, reason="needs chromium")


def _server():
    seen: list[tuple[str, str]] = []

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            seen.append((self.path, self.headers.get("User-Agent", "")))
            if self.path.startswith("/slow"):
                time.sleep(3)
            body = (
                b"<html><script>window.uaAtLoad = navigator.userAgent;"
                b"window.shadowMode = document.createElement('div').attachShadow({mode:'closed'}) === null"
                b"</script></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except BrokenPipeError:
                pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}", seen


@pytest.fixture
async def env():
    srv, base, seen = _server()
    browser = await asyncio.wait_for(zd.start(headless=True), 60)
    yield browser, base, seen
    await asyncio.wait_for(browser.stop(), 30)
    srv.shutdown()


def _doc_uas(seen, path):
    return [ua for p, ua in seen if p == path]


async def test_new_tab_first_document_has_no_headless_token(env):
    browser, base, seen = env
    await asyncio.wait_for(browser.get(base + "/main-tab"), 20)
    tab = await asyncio.wait_for(browser.get(base + "/new-tab", new_tab=True), 20)
    uas = _doc_uas(seen, "/new-tab")
    assert uas and not any("HeadlessChrome" in ua for ua in uas), uas
    assert "Headless" not in await tab.evaluate("window.uaAtLoad")
    # a new tab should look like a fresh tab, with a single history entry
    assert await tab.evaluate("history.length") == 1


async def test_create_context_first_document_has_no_headless_token(env):
    browser, base, seen = env
    tab = await asyncio.wait_for(browser.create_context(base + "/context"), 20)
    for _ in range(50):
        if _doc_uas(seen, "/context"):
            break
        await asyncio.sleep(0.1)
    uas = _doc_uas(seen, "/context")
    assert uas and not any("HeadlessChrome" in ua for ua in uas), uas
    _ = tab


async def test_new_tab_timeout_still_applies(env):
    """the get() timeout must keep covering a slow first navigation of a new tab"""
    browser, base, seen = env
    t = time.monotonic()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(browser.get(base + "/slow", new_tab=True, timeout=0.5), 20)
    assert time.monotonic() - t < 2
