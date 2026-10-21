import asyncio
import contextlib
import gc
import http.cookiejar
import json
import os
import pathlib
import pickle
import shutil
import subprocess
import sys
import weakref
from typing import Any, AsyncGenerator, AsyncIterator, Callable, Iterator

import psutil
import pytest
import websockets
from psutil import Process
from pytest_mock import MockerFixture
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

import zendriver as zd
from tests.conftest import CreateBrowser
from tests.sample_data import sample_file
from zendriver import cdp
from zendriver.core import util
from zendriver.core._contradict import ContraDict
from zendriver.core.connection import ProtocolException
from zendriver.core.proxy import ProxyForwarder, UpstreamProxy

# these tests exercise the browser lifecycle (e.g. stopping it)
pytestmark = pytest.mark.fresh_browser


async def test_connection_error_raises_exception_and_logs_stderr(
    create_browser: type[CreateBrowser],
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mocker.patch(
        "zendriver.core.browser.Browser.test_connection",
        return_value=False,
    )
    with caplog.at_level("INFO"):
        with pytest.raises(Exception):
            async with create_browser(
                browser_connection_max_tries=1, browser_connection_timeout=0.1
            ) as _:
                pass
    assert "Browser stderr" in caplog.text


async def test_get_content_gets_html_content(browser: zd.Browser) -> None:
    page = await browser.get(sample_file("groceries.html"))
    content = await page.get_content()
    assert content.lower().startswith("<!doctype html>")


async def test_update_target_sets_target_title(browser: zd.Browser) -> None:
    page = await browser.get(sample_file("groceries.html"))
    await page.wait_for_ready_state("complete")
    await page.update_target()
    assert page.target
    assert page.target.title == "Grocery List"


async def test_browser_stop_can_be_called_on_a_closed_connection(
    browser: zd.Browser,
) -> None:
    await browser.get(sample_file("groceries.html"))

    assert browser.connection is not None
    assert not browser.connection.closed

    await browser.connection.aclose()

    assert browser.connection.closed

    await browser.stop()
    assert browser.stopped


async def test_browser_stop_can_be_called_multiple_times(browser: zd.Browser) -> None:
    await browser.get(sample_file("groceries.html"))

    await browser.stop()
    assert browser.stopped

    await browser.stop()
    assert browser.stopped


async def test_browser_stop_exits_gracefully_without_kill(
    browser: zd.Browser, mocker: MockerFixture
) -> None:
    assert browser._process is not None
    kill = mocker.spy(browser._process, "kill")

    loop = asyncio.get_running_loop()
    start = loop.time()
    await browser.stop()
    elapsed = loop.time() - start

    assert browser.stopped
    kill.assert_not_called()
    assert elapsed < 2


async def test_browser_is_garbage_collected_after_stop(
    create_browser: type[CreateBrowser],
) -> None:
    browser = await zd.start(create_browser().config)
    await browser.get(sample_file("groceries.html"))
    await browser.stop()

    browser_ref = weakref.ref(browser)
    del browser
    gc.collect()

    assert browser_ref() is None


async def test_browser_stopped_is_true_after_calling_stop(browser: zd.Browser) -> None:
    await browser.get(sample_file("groceries.html"))
    await browser.stop()
    assert browser.stopped


async def test_browser_stopped_is_true_when_stopped_externally(
    browser: zd.Browser,
) -> None:
    await browser.get(sample_file("groceries.html"))
    assert not browser.stopped
    process = browser._process
    process_id = browser._process_pid

    # Check that we got the browser process info.
    assert process
    assert process_id

    psproc = Process(process_id)

    if browser.connection:
        # Stop the browser without using browser.stop() function to emulate a headful browser being closed by the user."
        await browser.connection.send(cdp.browser.close())
        await browser.connection.aclose()

    wait_attempts = 100
    wait_timeout = 0.2

    # "Wait up to {wait_timeout * wait_attempts} seconds for the process to terminate"
    for _ in range(wait_attempts):
        if not psproc.is_running():
            break
        try:
            psproc.wait(wait_timeout)
        except (TimeoutError, subprocess.TimeoutExpired, psutil.TimeoutExpired):
            # So many different exceptions... Why lib authors, why?
            continue

    assert not psproc.is_running()
    assert browser.stopped

    await browser.stop()


async def test_cookies_save_writes_only_the_cookies_matching_the_pattern(
    browser: zd.Browser,
    tmp_path: pathlib.Path,
) -> None:
    await browser.cookies.set_all(
        [
            cdp.network.CookieParam(
                name="wanted", value="nowsecure", domain="example.com", path="/"
            ),
            cdp.network.CookieParam(
                name="ignored", value="somethingelse", domain="example.com", path="/"
            ),
        ]
    )

    save_file = tmp_path / "cookies.dat"
    await browser.cookies.save(save_file, pattern="nowsecure")

    with save_file.open("rb") as f:
        saved = pickle.load(f)

    assert [cookie.name for cookie in saved] == ["wanted"]


async def test_cookies_save_and_load_round_trip(
    browser: zd.Browser,
    tmp_path: pathlib.Path,
) -> None:
    await browser.cookies.set_all(
        [
            cdp.network.CookieParam(
                name="kept", value="yes", domain="example.com", path="/"
            )
        ]
    )

    save_file = tmp_path / "cookies.dat"
    await browser.cookies.save(save_file)

    await browser.cookies.clear()
    assert await browser.cookies.get_all() == []

    await browser.cookies.load(save_file)

    restored = {cookie.name: cookie.value for cookie in await browser.cookies.get_all()}
    assert restored.get("kept") == "yes"


async def test_cookies_get_all_in_requests_cookie_format(
    browser: zd.Browser,
) -> None:
    await browser.cookies.set_all(
        [
            cdp.network.CookieParam(
                name="session_cookie",
                value="yes",
                domain="example.com",
                path="/",
                http_only=True,
            ),
            cdp.network.CookieParam(
                name="persistent_cookie",
                value="yes",
                domain="example.com",
                path="/",
                expires=cdp.network.TimeSinceEpoch(4102444800),
            ),
        ]
    )

    cookies = {
        cookie.name: cookie
        for cookie in await browser.cookies.get_all(requests_cookie_format=True)
    }

    session_cookie = cookies["session_cookie"]
    assert isinstance(session_cookie, http.cookiejar.Cookie)
    assert session_cookie.expires is None
    assert not session_cookie.is_expired()
    assert session_cookie.has_nonstandard_attr("HttpOnly")
    assert cookies["persistent_cookie"].expires is not None
    assert not cookies["persistent_cookie"].is_expired()
    assert not cookies["persistent_cookie"].has_nonstandard_attr("HttpOnly")


async def test_browser_starts_with_lang_option(
    create_browser: type[CreateBrowser],
) -> None:
    """Setting `lang` used to raise ValueError from Browser.start (#262)."""
    async with create_browser(lang="de-DE") as browser:
        assert "--lang=de-DE" in browser.config()
        page = await browser.get("about:blank")
        assert await page.evaluate("1 + 1") == 2


async def test_iframe_target_can_be_connected_to(
    browser: zd.Browser, cross_site_iframe_url: str
) -> None:
    """Connecting to iframe targets used to fail with a 404 (#275)."""
    await browser.get(cross_site_iframe_url)

    iframe_target = None
    for _ in range(50):
        iframe_target = next(
            (
                t
                for t in browser.targets
                if isinstance(t, zd.Tab) and t.type_ == "iframe"
            ),
            None,
        )
        if iframe_target is not None:
            break
        await asyncio.sleep(0.1)

    assert iframe_target is not None, "no iframe target was discovered"
    assert iframe_target.websocket_url.endswith(
        f"/devtools/page/{iframe_target.target_id}"
    )

    await iframe_target.select("#child")
    text = await iframe_target.evaluate("document.getElementById('child').innerText")
    assert text == "hello from iframe"


async def test_start_waits_for_initial_tab(
    create_browser: type[CreateBrowser], mocker: MockerFixture, headless: bool
) -> None:
    get_targets = zd.Browser._get_targets
    calls = 0

    async def get_targets_without_initial_tab(
        self: zd.Browser,
    ) -> list[cdp.target.TargetInfo]:
        nonlocal calls
        calls += 1
        targets = await get_targets(self)
        return targets if calls > 1 else [t for t in targets if t.type_ != "page"]

    mocker.patch.object(zd.Browser, "_get_targets", get_targets_without_initial_tab)
    browser_context = create_browser(headless=headless)
    browser_context.config.autodiscover_targets = False
    async with browser_context as browser:
        assert len(browser.tabs) == 1


async def test_pending_commands_fail_when_browser_process_dies(
    browser: zd.Browser,
) -> None:
    tab = await browser.get(sample_file("groceries.html"))
    assert browser.connection is not None
    assert browser._process_pid is not None

    process = Process(browser._process_pid)
    process.suspend()
    browser_command = asyncio.create_task(
        browser.connection.send(cdp.browser.get_version())
    )
    tab_command = asyncio.create_task(tab.send(cdp.page.get_frame_tree()))
    await asyncio.sleep(0.5)
    assert not browser_command.done()
    assert not tab_command.done()

    process.kill()
    results = await asyncio.wait_for(
        asyncio.gather(browser_command, tab_command, return_exceptions=True),
        timeout=10,
    )

    assert all(isinstance(result, Exception) for result in results)


async def test_pending_commands_fail_when_connection_is_closed(
    browser: zd.Browser,
) -> None:
    await browser.get(sample_file("groceries.html"))
    assert browser.connection is not None
    assert browser._process_pid is not None

    process = Process(browser._process_pid)
    process.suspend()
    try:
        browser_command = asyncio.create_task(
            browser.connection.send(cdp.browser.get_version())
        )
        await asyncio.sleep(0.5)
        assert not browser_command.done()

        await browser.connection.aclose()

        with pytest.raises(ProtocolException):
            await asyncio.wait_for(browser_command, timeout=10)
    finally:
        process.resume()


async def test_get_tab_matches_url_and_title(browser: zd.Browser) -> None:
    tab = await browser.get(sample_file("groceries.html"))
    await tab.wait_for_ready_state("complete")

    assert await browser.get_tab("groceries.html") is tab
    assert await browser.get_tab("grocery list") is tab
    assert await browser.get_tab("does-not-exist") is None


def _exception_group() -> BaseException:
    if sys.version_info >= (3, 11):
        return ExceptionGroup("group", [ValueError("inner")])  # noqa: F821
    pytest.skip("ExceptionGroup needs Python 3.11+")


@pytest.mark.parametrize(
    "make_exception",
    [
        pytest.param(
            lambda: json.JSONDecodeError("Expecting value", "{bad", 1), id="json"
        ),
        pytest.param(
            lambda: websockets.exceptions.ConnectionClosedError(None, None),
            id="connection-closed",
        ),
        pytest.param(
            lambda: ProtocolException({"code": -32000, "message": "No node found"}),
            id="protocol",
        ),
        pytest.param(lambda: SystemExit(3), id="system-exit"),
        pytest.param(_exception_group, id="exception-group"),
    ],
)
async def test_aexit_propagates_the_original_exception(
    make_exception: Callable[[], BaseException], tmp_path: pathlib.Path
) -> None:
    # never started: the fake path skips the browser lookup and tmp_path keeps
    # Config from creating a temporary profile directory
    browser = zd.Browser(
        zd.Config(browser_executable_path="/path/to/browser", user_data_dir=tmp_path)
    )

    exception = make_exception()
    with pytest.raises(type(exception)) as exc_info:
        async with browser:
            raise exception

    assert exc_info.value is exception


class FailingWebSocket:
    """Fails every command, and records the methods it was sent."""

    def __init__(self) -> None:
        self.closed = False
        self.methods: list[str] = []
        self._replies: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: str) -> None:
        command = json.loads(message)
        self.methods.append(command["method"])
        error = {"code": -32000, "message": "simulated failure"}
        self._replies.put_nowait(json.dumps({"id": command["id"], "error": error}))

    async def recv(self) -> str:
        return await self._replies.get()

    async def close(self) -> None:
        # yield like a real close handshake, so the cancelled listener stops first
        await asyncio.sleep(0)
        self.closed = True


class FakeBrowser:
    """Stands in for the browser that Browser.start launches or attaches to."""

    def __init__(self) -> None:
        self.answers = True
        self.browser: zd.Browser | None = None
        self.processes: list[subprocess.Popen[bytes]] = []
        self.websocket = FailingWebSocket()

    def start_process(self, *args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        # a process that runs until it is stopped, in place of the browser
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes.append(process)
        return process

    async def test_connection(self, browser: zd.Browser) -> bool:
        self.browser = browser
        if self.answers:
            browser.info = ContraDict(
                {"webSocketDebuggerUrl": "ws://127.0.0.1:1/devtools/browser/fake"},
                silent=True,
            )
        return self.answers

    async def start(self, timeout: float, **kwargs: Any) -> BaseException | None:
        """returns what zd.start() raised, with a safety net that does not rely on it"""
        task = asyncio.ensure_future(
            asyncio.wait_for(
                zd.start(browser_executable_path=sys.executable, **kwargs), timeout
            )
        )
        done, _ = await asyncio.wait({task}, timeout=timeout + 20)
        if not done:
            task.cancel()
            pytest.fail("start() did not return")
        return task.exception()

    @property
    def profile(self) -> pathlib.Path:
        assert self.browser is not None
        return pathlib.Path(self.browser.config.user_data_dir)


@pytest.fixture
async def fake_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[FakeBrowser, None]:
    fake = FakeBrowser()
    registered = set(util.get_registered_instances())

    async def connect(*args: Any, **kwargs: Any) -> FailingWebSocket:
        return fake.websocket

    async def test_connection(browser: zd.Browser) -> bool:
        return await fake.test_connection(browser)

    monkeypatch.setattr(util, "_start_process", fake.start_process)
    monkeypatch.setattr(zd.Browser, "test_connection", test_connection)
    monkeypatch.setattr(websockets, "connect", connect)
    yield fake

    # never leave anything behind, whatever start() did
    for browser in util.get_registered_instances() - registered:
        util.get_registered_instances().discard(browser)
        if browser.connection:
            await browser.connection.aclose()
    for process in fake.processes:
        if process.poll() is None:
            process.kill()
            process.wait()
    if fake.browser is not None:
        shutil.rmtree(fake.profile, ignore_errors=True)


async def test_cancelled_start_stops_the_launched_browser(
    fake_browser: FakeBrowser,
) -> None:
    # the browser never answers, so start() is still retrying when it is cancelled
    fake_browser.answers = False
    error = await fake_browser.start(
        0.5, browser_connection_timeout=0.05, browser_connection_max_tries=1000
    )

    assert isinstance(error, asyncio.TimeoutError)
    assert len(fake_browser.processes) == 1
    assert fake_browser.processes[0].poll() is not None, "browser is still running"
    assert not fake_browser.profile.exists(), "temporary profile was left behind"
    assert fake_browser.browser not in util.get_registered_instances()


async def test_failed_start_stops_the_launched_browser(
    fake_browser: FakeBrowser,
) -> None:
    error = await fake_browser.start(10)

    assert isinstance(error, ProtocolException)
    assert len(fake_browser.processes) == 1
    assert fake_browser.processes[0].poll() is not None, "browser is still running"
    assert not fake_browser.profile.exists(), "temporary profile was left behind"
    assert fake_browser.browser not in util.get_registered_instances()
    assert fake_browser.websocket.closed


async def test_failed_start_does_not_close_an_attached_browser(
    fake_browser: FakeBrowser,
) -> None:
    # host and port given: start() attaches to a running browser instead of launching one
    error = await fake_browser.start(10, host="127.0.0.1", port=9222)

    assert isinstance(error, ProtocolException)
    assert fake_browser.processes == []
    assert "Browser.close" not in fake_browser.websocket.methods
    assert fake_browser.websocket.closed
    assert not fake_browser.profile.exists(), "temporary profile was left behind"
    assert fake_browser.browser not in util.get_registered_instances()


# python programs which stand in for the browser process in the stop() tests
# below, so that these need no browser. each prints "ready" once it can be stopped
EXITS_ON_SIGTERM = "import time; print('ready', flush=True); time.sleep(60)"
EXITS_A_WHILE_AFTER_SIGTERM = """
import os, signal, time
def exit_soon(*_):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(0.4)
    os._exit(0)
signal.signal(signal.SIGTERM, exit_soon)
print('ready', flush=True)
time.sleep(60)
"""
IGNORES_SIGTERM = """
import signal, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
print('ready', flush=True)
time.sleep(60)
"""

StubBrowserFactory = Callable[..., tuple[zd.Browser, subprocess.Popen[bytes]]]


@pytest.fixture
def stub_browser() -> Iterator[StubBrowserFactory]:
    """creates browsers whose process runs one of the programs above"""
    created: list[tuple[zd.Browser, subprocess.Popen[bytes]]] = []

    def create(
        program: str = EXITS_ON_SIGTERM,
    ) -> tuple[zd.Browser, subprocess.Popen[bytes]]:
        browser = zd.Browser(zd.Config(browser_executable_path=sys.executable))
        # creates the temporary profile, as start() does
        assert os.path.isdir(browser.config.user_data_dir)
        process = subprocess.Popen(
            [sys.executable, "-c", program], stdout=subprocess.PIPE
        )
        created.append((browser, process))
        assert process.stdout is not None
        assert process.stdout.readline().strip() == b"ready"
        browser._process, browser._process_pid = process, process.pid
        return browser, process

    yield create
    for browser, process in created:
        if process.poll() is None:
            process.kill()
        process.wait()
        if process.stdout is not None:
            process.stdout.close()
        shutil.rmtree(browser.config.user_data_dir, ignore_errors=True)


@contextlib.asynccontextmanager
async def _fake_chrome(
    method: str, misbehave: Callable[[ServerConnection], None]
) -> AsyncIterator[str]:
    """
    serves a cdp peer which answers every command with an empty result, except
    `method`, on which it calls `misbehave` instead. yields its websocket url
    """

    async def handler(websocket: ServerConnection) -> None:
        with contextlib.suppress(ConnectionClosed):
            async for raw in websocket:
                message = json.loads(raw)
                if message["method"] == method:
                    misbehave(websocket)
                    continue
                result: dict[str, Any] = {}
                if message["method"] == "Target.attachToTarget":
                    target_id = message["params"]["targetId"]
                    result = {"sessionId": f"session-{target_id}"}
                reply: dict[str, Any] = {"id": message["id"], "result": result}
                if "sessionId" in message:
                    reply["sessionId"] = message["sessionId"]
                await websocket.send(json.dumps(reply))

    async with serve(handler, "127.0.0.1", 0) as server:
        port = list(server.sockets)[0].getsockname()[1]
        yield f"ws://127.0.0.1:{port}/devtools/browser/fake"


async def _attach_tabs(browser: zd.Browser, websocket_url: str, count: int) -> None:
    browser.connection = zd.Connection(websocket_url, _owner=browser)
    for i in range(count):
        target = cdp.target.TargetInfo(
            target_id=cdp.target.TargetID(f"tab-{i}"),
            type_="page",
            title="",
            url="about:blank",
            attached=False,
            can_access_opener=False,
        )
        tab = zd.Tab(websocket_url, target=target, browser=browser)
        browser.targets.append(tab)
        await tab.aopen()
        assert tab.session_id is not None


@pytest.mark.parametrize("method", ["Target.detachFromTarget", "Browser.close"])
async def test_browser_stop_terminates_a_browser_which_stopped_responding(
    method: str, stub_browser: StubBrowserFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("zendriver.core.browser.STOP_COMMAND_TIMEOUT", 0.5)
    browser, process = stub_browser()
    async with _fake_chrome(method, lambda websocket: None) as websocket_url:
        await _attach_tabs(browser, websocket_url, 2)

        stop = asyncio.create_task(browser.stop())
        done, _ = await asyncio.wait({stop}, timeout=10)
        if not done:
            stop.cancel()
            await asyncio.gather(stop, return_exceptions=True)
        assert done, f"stop() still waits for the {method} reply"
        await stop

    assert process.poll() is not None
    assert not os.path.exists(browser.config.user_data_dir)


async def test_browser_stop_cleans_up_when_the_connection_drops_while_detaching(
    stub_browser: StubBrowserFactory,
) -> None:
    browser, process = stub_browser()
    # like a browser which crashed: the connection ends without a close frame
    async with _fake_chrome(
        "Target.detachFromTarget", lambda websocket: websocket.transport.abort()
    ) as websocket_url:
        await _attach_tabs(browser, websocket_url, 2)

        await asyncio.wait_for(browser.stop(), timeout=10)

    assert browser._process is None
    assert process.poll() is not None
    assert not os.path.exists(browser.config.user_data_dir)


async def test_concurrent_browser_stop_calls_do_not_raise(
    stub_browser: StubBrowserFactory,
) -> None:
    # the process takes a while to exit, so that both calls wait for it
    browser, process = stub_browser(EXITS_A_WHILE_AFTER_SIGTERM)

    first = asyncio.create_task(browser.stop())
    await asyncio.sleep(0.1)
    second = asyncio.create_task(browser.stop())
    results = await asyncio.wait_for(
        asyncio.gather(first, second, return_exceptions=True), timeout=10
    )

    assert list(results) == [None, None]
    assert process.poll() is not None
    assert not os.path.exists(browser.config.user_data_dir)


async def test_cancelled_browser_stop_leaves_no_unretrieved_exception(
    stub_browser: StubBrowserFactory,
) -> None:
    browser, process = stub_browser()
    loop = asyncio.get_running_loop()
    # so that garbage left by earlier tests does not reach the handler below
    gc.collect()
    contexts: list[dict[str, Any]] = []
    handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda loop, context: contexts.append(context))
    try:
        detaching = asyncio.Event()
        async with _fake_chrome(
            "Target.detachFromTarget", lambda websocket: detaching.set()
        ) as websocket_url:
            await _attach_tabs(browser, websocket_url, 2)

            # cancelled while it waits for the detach replies, as by a ctrl+c
            # or by asyncio.wait_for(browser.stop(), timeout)
            stop = asyncio.create_task(browser.stop())
            await asyncio.wait_for(detaching.wait(), timeout=10)
            stop.cancel()
            await asyncio.wait({stop}, timeout=10)
            assert stop.cancelled()
            # python < 3.12 reports an exception which was never retrieved
            # once the futures of the cancelled stop() are collected
            del stop
            gc.collect()

            await asyncio.wait_for(browser.stop(), timeout=10)
    finally:
        loop.set_exception_handler(handler)

    assert not [
        context for context in contexts if "never retrieved" in context["message"]
    ], contexts
    assert process.poll() is not None
    assert not os.path.exists(browser.config.user_data_dir)


@pytest.mark.parametrize("closes", ["once_the_browser_is_gone", "never"])
async def test_browser_stop_closes_proxy_forwarders_once_the_browser_is_gone(
    closes: str, stub_browser: StubBrowserFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("zendriver.core.browser.STOP_COMMAND_TIMEOUT", 0.5)
    browser, process = stub_browser()
    forwarder = ProxyForwarder(UpstreamProxy("http", "127.0.0.1", 1, "user", "pass"))
    closed = asyncio.Event()

    async def close() -> None:
        # as ProxyForwarder.close() does on python >= 3.12.1, which waits until
        # the browser's connections to the forwarder are closed
        while closes == "never" or process.poll() is None:
            await asyncio.sleep(0.05)
        closed.set()

    monkeypatch.setattr(forwarder, "close", close)
    browser._proxy_forwarders.append(forwarder)

    stop = asyncio.create_task(browser.stop())
    done, _ = await asyncio.wait({stop}, timeout=10)
    if not done:
        stop.cancel()
        await asyncio.gather(stop, return_exceptions=True)
    assert done, "stop() still waits for the proxy forwarder to close"
    await stop

    assert closed.is_set() == (closes == "once_the_browser_is_gone")
    assert not browser._proxy_forwarders
    assert process.poll() is not None
    assert not os.path.exists(browser.config.user_data_dir)


async def test_browser_stop_keeps_a_process_started_while_it_ran(
    stub_browser: StubBrowserFactory,
) -> None:
    browser, process = stub_browser(EXITS_A_WHILE_AFTER_SIGTERM)

    stop = asyncio.create_task(browser.stop())
    await asyncio.sleep(0.1)
    # as if the browser was started again while stop() waits for the old process
    _, new_process = stub_browser()
    browser._process, browser._process_pid = new_process, new_process.pid
    await asyncio.wait_for(stop, timeout=10)

    assert process.poll() is not None
    assert browser._process is new_process
    assert browser._process_pid == new_process.pid


ATEXIT_SCRIPT = """
import asyncio, subprocess, sys
import asyncio_atexit
import zendriver as zd

async def main():
    browser = zd.Browser(zd.Config(browser_executable_path=sys.executable))
    process = subprocess.Popen(
        [sys.executable, "-c", sys.argv[1]],
        stdout=subprocess.PIPE,
        # so that a process which is left running does not hold the test's pipe
        stderr=subprocess.DEVNULL,
    )
    assert process.stdout.readline().strip() == b"ready"
    browser._process, browser._process_pid = process, process.pid
    asyncio_atexit.register(browser._atexit_cleanup)  # as Browser.create does
    print(process.pid, flush=True)
    print(browser.config.user_data_dir, flush=True)
    if sys.argv[2] == "cancelled":
        try:
            await asyncio.wait_for(browser.stop(), 0.5)
        except asyncio.TimeoutError:
            pass

asyncio.run(main())
"""


@pytest.mark.parametrize(
    "program, stop",
    [(EXITS_ON_SIGTERM, "never"), (IGNORES_SIGTERM, "cancelled")],
    ids=["stop_never_called", "stop_cancelled"],
)
def test_atexit_cleanup_stops_the_browser_under_asyncio_run(
    program: str, stop: str
) -> None:
    # asyncio.run shuts the default executor down before it closes the loop,
    # which is when asyncio_atexit runs the cleanup
    result = subprocess.run(
        [sys.executable, "-c", ATEXIT_SCRIPT, program, stop],
        capture_output=True,
        text=True,
        timeout=60,
    )
    lines = result.stdout.splitlines()
    assert len(lines) == 2, result.stderr
    pid, user_data_dir = int(lines[0]), lines[1]
    try:
        assert result.returncode == 0, result.stderr
        assert "Unhandled exception" not in result.stderr, result.stderr
        assert not psutil.pid_exists(pid), "the browser process outlived python"
        assert not os.path.exists(user_data_dir)
    finally:
        with contextlib.suppress(psutil.NoSuchProcess):
            Process(pid).kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)
