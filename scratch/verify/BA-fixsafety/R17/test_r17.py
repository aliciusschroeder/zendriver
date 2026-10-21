"""Regression tests for group R17 (Browser.get wait semantics). Needs real chromium."""

import asyncio
import http.server
import shutil
import threading
import time

import pytest

import zendriver as zd
from zendriver import cdp

print("\nzendriver imported from", zd.__file__)

pytestmark = pytest.mark.skipif(shutil.which("chromium") is None, reason="needs chromium")


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/204"):
            self.send_response(204)
            self.end_headers()
            return
        if self.path.startswith("/dl"):
            body = b"x" * 10
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", "attachment; filename=r17.bin")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/slow"):
            time.sleep(3)
        body = b"<html><title>p</title></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass


@pytest.fixture
async def env():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = await asyncio.wait_for(zd.start(headless=True), 60)
    # never write downloads to disk
    await browser.connection.send(cdp.browser.set_download_behavior("deny"))
    yield browser, f"http://127.0.0.1:{srv.server_address[1]}"
    await asyncio.wait_for(browser.stop(), 30)
    srv.shutdown()


async def _page_ids(browser):
    return {t.target_id for t in await browser._get_targets() if t.type_ == "page"}


async def test_get_returns_for_204(env):
    browser, base = env
    await asyncio.wait_for(browser.get(base + "/page", timeout=3), 20)
    t = time.monotonic()
    tab = await asyncio.wait_for(browser.get(base + "/204", timeout=3), 20)
    assert time.monotonic() - t < 2
    assert tab is browser.tabs[0]


async def test_get_returns_for_download(env):
    browser, base = env
    await asyncio.wait_for(browser.get(base + "/page", timeout=3), 20)
    tab = await asyncio.wait_for(browser.get(base + "/dl", timeout=3), 20)
    assert tab is browser.tabs[0]


async def test_get_new_tab_timeout_does_not_leave_the_tab_open(env):
    browser, base = env
    before = await _page_ids(browser)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            browser.get(base + "/slow", new_tab=True, timeout=0.5), 20
        )
    for _ in range(30):
        after = await _page_ids(browser)
        if after == before:
            break
        await asyncio.sleep(0.1)
    assert after == before


async def test_get_regular_navigation_still_waits(env):
    browser, base = env
    tab = await asyncio.wait_for(browser.get(base + "/page", timeout=3), 20)
    assert tab.target.url.endswith("/page")
    tab2 = await asyncio.wait_for(browser.get(base + "/page2", new_tab=True, timeout=5), 20)
    assert tab2.target.url.endswith("/page2")
