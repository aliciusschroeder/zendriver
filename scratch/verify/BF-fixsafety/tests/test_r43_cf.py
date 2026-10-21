import asyncio
import http.server
import threading
from typing import Any

import pytest

import zendriver as zd
from zendriver.core import cloudflare as cloudflare_module
from zendriver.core.connection import ProtocolException


def test_print_origin() -> None:
    print("zendriver imported from", zd.__file__)


# ---------------------------------------------------------------- browser-free


class _StaleInput:
    """an input element whose node was replaced by a navigation"""

    def __init__(self) -> None:
        self.attrs: dict[str, str] = {}
        self.gone = False

    async def update(self) -> "_StaleInput":
        if self.gone:
            raise ProtocolException(
                {"code": -32000, "message": "Node with given id does not belong to the document"}
            )
        return self

    def __await__(self) -> Any:
        return self.update().__await__()


async def test_verify_cf_navigation_after_click_is_success(monkeypatch: pytest.MonkeyPatch) -> None:
    iframe_node = zd.cdp.dom.Node(
        node_id=zd.cdp.dom.NodeId(42),
        backend_node_id=zd.cdp.dom.BackendNodeId(42),
        node_type=1,
        node_name="DIV",
        local_name="div",
        node_value="",
    )

    class _Iframe:
        node = iframe_node

        async def scroll_into_view(self) -> None:
            pass

    async def fake_wait(_tab: Any, _timeout: float) -> tuple[Any, Any, Any]:
        return object(), object(), _Iframe()

    monkeypatch.setattr(cloudflare_module, "cf_wait_for_interactive_challenge", fake_wait)
    box = zd.cdp.dom.BoxModel(
        content=zd.cdp.dom.Quad([0.0, 0.0, 100.0, 0.0, 100.0, 50.0, 0.0, 50.0]),
        padding=zd.cdp.dom.Quad([]),
        border=zd.cdp.dom.Quad([]),
        margin=zd.cdp.dom.Quad([]),
        width=100,
        height=50,
    )

    async def fake_send(cdp_obj: Any, _is_update: bool = False) -> Any:
        next(cdp_obj)
        return box

    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "send", fake_send)
    stale = _StaleInput()

    async def fake_query_selector(selector: str) -> Any:
        return None if stale.gone else stale

    async def fake_click(x: float, y: float) -> None:
        stale.gone = True  # the challenge redirects to the real site

    monkeypatch.setattr(tab, "query_selector", fake_query_selector)
    monkeypatch.setattr(tab, "mouse_click", fake_click)
    await asyncio.wait_for(cloudflare_module.verify_cf(tab, click_delay=0, timeout=5), 20)


# ---------------------------------------------------------------- real chromium

PAGE = """<!doctype html><html><body>
<div id=host style="width:300px;height:65px"></div>
<input type=hidden name=cf-turnstile-response>
<script>
const sr = document.getElementById('host').attachShadow({mode: 'closed'});
const d = document.createElement('div');
d.setAttribute('data-src', 'https://challenges.cloudflare.com/x');
d.style.cssText = 'width:300px;height:65px;background:#ccc';
sr.appendChild(d);
d.addEventListener('click', () => {
  const mode = new URLSearchParams(location.search).get('mode');
  const input = document.querySelector('input[name=cf-turnstile-response]');
  if (mode === 'navigate') location.href = '/solved';
  else if (mode === 'value') input.value = 'token';
  else if (mode === 'remove') input.remove();
});
</script></body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = (PAGE if self.path.startswith("/challenge") else "<p>solved</p>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture(scope="module")
def server():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


@pytest.mark.parametrize("mode", ["navigate", "value", "remove"])
async def test_verify_cf_real_chromium(server: str, mode: str) -> None:
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f"{server}/challenge?mode={mode}")
        await asyncio.wait_for(tab.verify_cf(click_delay=1, timeout=10), 30)
        if mode == "navigate":
            await tab.sleep(0.5)
            assert tab.url.endswith("/solved") or (await tab.evaluate("location.pathname")) == "/solved"
    finally:
        await browser.stop()
