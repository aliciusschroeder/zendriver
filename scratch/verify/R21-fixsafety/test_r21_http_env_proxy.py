"""Regression test for R21: HTTPApi must reach the DevTools HTTP endpoint
directly, not through the http_proxy of the environment."""

import http.server
import json
import threading
import urllib.request
from typing import Iterator

import pytest

import zendriver
from zendriver.core.browser import HTTPApi

print("zendriver imported from", zendriver.__file__)

VERSION = {"Browser": "Fake/1.0", "webSocketDebuggerUrl": "ws://127.0.0.1:1/x"}


class _DevTools(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps(VERSION if self.path == "/json/version" else []).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


class _Proxy(http.server.BaseHTTPRequestHandler):
    seen: list[str] = []

    def do_GET(self) -> None:
        # a corporate proxy cannot reach the loopback of the user's machine
        type(self).seen.append(self.requestline)
        self.send_error(502, "proxy cannot reach loopback")

    def log_message(self, *args: object) -> None:
        pass


def _serve(handler: type) -> http.server.ThreadingHTTPServer:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def servers() -> Iterator[tuple[http.server.ThreadingHTTPServer, http.server.ThreadingHTTPServer]]:
    _Proxy.seen = []
    devtools, proxy = _serve(_DevTools), _serve(_Proxy)
    yield devtools, proxy
    for s in (devtools, proxy):
        s.shutdown()
        s.server_close()


@pytest.mark.parametrize("var", ["http_proxy", "HTTP_PROXY"])
async def test_http_api_does_not_use_env_proxy(
    servers: tuple[http.server.ThreadingHTTPServer, http.server.ThreadingHTTPServer],
    monkeypatch: pytest.MonkeyPatch,
    var: str,
) -> None:
    devtools, proxy = servers
    for name in (
        "no_proxy", "NO_PROXY", "http_proxy", "HTTP_PROXY", "all_proxy",
        "ALL_PROXY", "REQUEST_METHOD",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(var, "http://127.0.0.1:%d" % proxy.server_address[1])
    # urlopen caches the proxies of the environment in its global opener on its
    # first call: start from a fresh one, so earlier tests cannot hide the proxy
    monkeypatch.setattr(urllib.request, "_opener", None)

    api = HTTPApi(("127.0.0.1", devtools.server_address[1]))
    assert await api.get("version") == VERSION
    assert await api.get("") == []
    assert _Proxy.seen == []
