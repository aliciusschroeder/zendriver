import asyncio
import functools
import http.server
import pathlib
import threading
import warnings

import pytest

import zendriver

print("zendriver imported from", zendriver.__file__)


def test_where() -> None:
    print("zendriver imported from", zendriver.__file__)


def ls(d: pathlib.Path) -> list[str]:
    return sorted(str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()) if d.exists() else []


async def wait_file(root: pathlib.Path, name: str, t: float = 4) -> bool:
    for _ in range(int(t * 10)):
        if any(f.endswith(name) for f in ls(root)):
            return True
        await asyncio.sleep(0.1)
    return False


async def click_dl(tab, name: str) -> None:
    await tab.evaluate(
        "(()=>{const a=document.createElement('a');a.href='/data.txt';"
        f"a.download='{name}';document.body.appendChild(a);a.click();}})()"
    )


@pytest.fixture
async def env(tmp_path, monkeypatch):
    www = tmp_path / "www"
    www.mkdir()
    (www / "index.html").write_text("<html><body>x</body></html>")
    (www / "data.txt").write_text("hello\n")
    work = tmp_path / "work"
    work.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setenv("HOME", str(home))  # chrome's default download dir
    warnings.simplefilter("ignore")
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(www))
    h.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = await zendriver.start(headless=True)
    try:
        yield browser, f"http://127.0.0.1:{srv.server_port}", tmp_path
    finally:
        await browser.stop()
        srv.shutdown()


async def test_download_file_inside_expect_download_delivers_event(env) -> None:
    browser, base, root = env
    tab = await browser.get(base + "/index.html")
    async with tab.expect_download() as ex:
        await tab.download_file(base + "/data.txt", "x.txt")
        ev = await asyncio.wait_for(ex.value, 5)
        assert ev.suggested_filename == "x.txt"
    await asyncio.sleep(0.5)
    assert not any(f.endswith("x.txt") for f in ls(root)), ls(root)  # denied


async def test_download_file_on_second_tab_keeps_path(env) -> None:
    browser, base, root = env
    dir_a = root / "dirA"
    tab_a = await browser.get(base + "/index.html")
    await tab_a.set_download_path(dir_a)
    tab_b = await browser.get(base + "/index.html", new_tab=True)
    await tab_b.download_file(base + "/data.txt", "b.txt")
    assert await wait_file(root, "b.txt")
    await click_dl(tab_a, "fromA.txt")
    assert await wait_file(root, "fromA.txt")
    assert "dirA/fromA.txt" in ls(root), ls(root)


async def test_expect_download_on_other_tab_keeps_path(env) -> None:
    browser, base, root = env
    dir_b = root / "dirB"
    tab_b = await browser.get(base + "/index.html")
    await tab_b.set_download_path(dir_b)
    tab_c = await browser.get(base + "/index.html", new_tab=True)
    async with tab_c.expect_download():
        pass
    await tab_b.download_file(base + "/data.txt", "second.txt")
    assert await wait_file(root, "second.txt")
    assert "dirB/second.txt" in ls(root), ls(root)


async def test_context_tab_download_path_and_expectation(env) -> None:
    browser, base, root = env
    tab = await browser.get(base + "/index.html")
    await tab.set_download_path(root / "dirDef")
    ctx_tab = await browser.create_context(base + "/index.html")
    await ctx_tab.wait_for_ready_state("complete")
    await ctx_tab.set_download_path(root / "dirCtx")
    await click_dl(ctx_tab, "ctx1.txt")
    assert await wait_file(root, "ctx1.txt")
    assert "dirCtx/ctx1.txt" in ls(root), ls(root)
    async with ctx_tab.expect_download() as ex:
        await click_dl(ctx_tab, "ctx2.txt")
        ev = await asyncio.wait_for(ex.value, 5)
        assert ev.suggested_filename == "ctx2.txt"
    # the default context kept its own path
    await click_dl(tab, "def.txt")
    assert await wait_file(root, "def.txt")
    assert "dirDef/def.txt" in ls(root), ls(root)
