import asyncio
import builtins
import functools
import http.server
import io
import os
import pathlib
import threading

import pytest

import zendriver
from zendriver import cdp
from zendriver.core import tab as tab_module
from zendriver.core.tab import Tab

print("zendriver imported from", zendriver.__file__)


def test_where() -> None:
    print("zendriver imported from", zendriver.__file__)


def fake_tab() -> Tab:
    target = cdp.target.TargetInfo(
        target_id=cdp.target.TargetID("T"), type_="page", title="",
        url="http://example.com/docs/index.html", attached=True, can_access_opener=False,
    )
    t = Tab("ws://127.0.0.1:9/devtools/page/T", target=target)

    async def sleep(*a, **k):
        return None

    t.sleep = sleep
    return t


async def test_save_snapshot_keeps_crlf_with_windows_text_mode(tmp_path, monkeypatch) -> None:
    """emulates windows: text mode without newline= translates \\n into \\r\\n"""
    snapshot = "From: <Saved by Blink>\r\nSubject: x\r\n\r\n------b\r\nbody\r\n"
    t = fake_tab()

    async def send(cdp_obj, _is_update=False):
        request = next(cdp_obj)
        assert request["method"] == "Page.captureSnapshot"
        try:
            cdp_obj.send({"data": snapshot})
        except StopIteration as e:
            return e.value

    t.send = send
    real_open = builtins.open

    def windows_open(file, mode="r", *args, **kwargs):
        if "b" not in mode and "w" in mode and "newline" not in kwargs and len(args) < 3:
            kwargs["newline"] = "\r\n"
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(tab_module, "open", windows_open, raising=False)
    out = tmp_path / "s.mhtml"
    await t.save_snapshot(str(out))
    assert out.read_bytes() == snapshot.encode()


# ---------------- real chromium ----------------

PAGE = """<html><head><link href="style.css" rel=stylesheet></head><body>
<a href="sub/page.html">a</a><img src="images/a.png"><a href="other.html">o</a>
<a href="../up.html">u</a><a href="/root.html">r</a>
<a href="https://example.org/page#frag">x</a><a href="#top">t</a></body></html>"""


@pytest.fixture
async def env(tmp_path, monkeypatch):
    root = tmp_path / "www"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "index.html").write_text(PAGE)
    (root / "docs" / "data.txt").write_text("hello data\n")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    h.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = await zendriver.start(headless=True)
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        tab = await browser.get(base + "/docs/index.html")
        await tab.wait_for_ready_state("complete")
        yield browser, tab, base, work
    finally:
        await browser.stop()
        srv.shutdown()


async def test_get_all_urls_resolves_against_page_url(env) -> None:
    _, tab, base, _ = env
    urls = await tab.get_all_urls()
    assert sorted(urls) == sorted([
        base + "/docs/style.css", base + "/docs/sub/page.html", base + "/docs/images/a.png",
        base + "/docs/other.html", base + "/up.html", base + "/root.html",
        "https://example.org/page#frag",
    ])


async def test_set_user_agent_keeps_client_hints_headless(env) -> None:
    browser, tab, _, _ = env
    assert browser.headless_user_agent is not None
    before = await tab.evaluate("navigator.userAgentData.brands.length")
    assert before > 0
    await tab.set_user_agent(accept_language="de-DE")
    await tab.reload()
    await tab.wait_for_ready_state("complete")
    assert await tab.evaluate("navigator.language") == "de-DE"
    assert await tab.evaluate("navigator.userAgentData.brands.length") == before
    assert await tab.evaluate("navigator.userAgentData.platform") != ""
    # an explicit different user agent still works (no metadata for it)
    await tab.set_user_agent("Custom/1.0")
    await tab.reload()
    assert await tab.evaluate("navigator.userAgent") == "Custom/1.0"


async def test_download_file_with_quote_in_filename(env) -> None:
    _, tab, base, work = env
    dl = work / "dl"
    await tab.set_download_path(dl)
    await tab.download_file(base + "/docs/data.txt", "O'Reilly \\ x.txt")
    await tab.download_file(base + "/docs/data.txt", "x'); window.__pwned=1; ('")
    for _ in range(50):
        if len([f for f in os.listdir(dl) if not f.endswith(".crdownload")]) >= 2:
            break
        await asyncio.sleep(0.1)
    files = sorted(os.listdir(dl))
    assert any("Reilly" in f for f in files), files
    assert await tab.evaluate("window.__pwned === 1") is False


async def test_save_screenshot_webp_and_unique_auto_names(env) -> None:
    _, tab, _, work = env
    p = await tab.save_screenshot(format="webp")
    assert p.endswith(".webp") and os.path.getsize(p) > 0
    p1 = await tab.save_screenshot()
    p2 = await tab.save_screenshot()
    p3, p4 = await asyncio.gather(tab.save_screenshot(), tab.save_screenshot())
    assert len({p1, p2, p3, p4}) == 4, (p1, p2, p3, p4)
    assert all(os.path.exists(x) for x in (p1, p2, p3, p4))


async def test_print_to_pdf_stream(env) -> None:
    _, tab, _, work = env
    p = await tab.print_to_pdf(work / "s.pdf", transfer_mode="ReturnAsStream")
    data = p.read_bytes()
    assert data.startswith(b"%PDF") and len(data) > 1000
    p2 = await tab.print_to_pdf(work / "b.pdf")
    assert p2.read_bytes().startswith(b"%PDF")
