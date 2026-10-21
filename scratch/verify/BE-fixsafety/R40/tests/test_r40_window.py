import pytest

import zendriver
from zendriver import cdp
from zendriver.core.tab import Tab

print("zendriver imported from", zendriver.__file__)


class FakeChromeWindow:
    """models chrome's BrowserHandler::SetWindowBounds state machine"""

    def __init__(self) -> None:
        self.state = "normal"
        self.normal = [10, 10, 780, 580]  # restore geometry
        self.calls: list[dict] = []

    def bounds(self) -> dict:
        if self.state == "normal":
            l, t, w, h = self.normal
        else:
            l, t, w, h = 0, 0, 800, 600
        return {"left": l, "top": t, "width": w, "height": h, "windowState": self.state}

    def handle(self, method: str, params: dict) -> dict:
        if method == "Browser.getWindowForTarget":
            return {"windowId": 1, "bounds": self.bounds()}
        assert method == "Browser.setWindowBounds"
        self.calls.append(params["bounds"])
        b = params["bounds"]
        want = b.get("windowState", "normal")
        geo = [b.get(k) for k in ("left", "top", "width", "height")]
        set_bounds = any(g is not None for g in geo)
        if set_bounds and want != "normal":
            raise zendriver.core.connection.ProtocolException("cannot combine")
        if want == "normal":
            if self.state != "normal":
                self.state = "normal"  # restore, geometry ignored
            elif set_bounds:
                self.normal = [g if g is not None else o for g, o in zip(geo, self.normal)]
        elif want == "maximized":
            if self.state in ("minimized", "fullscreen"):
                raise zendriver.core.connection.ProtocolException("restore first")
            self.state = want
        elif want == "minimized":
            if self.state == "fullscreen":
                raise zendriver.core.connection.ProtocolException("restore first")
            self.state = want
        elif want == "fullscreen":
            if self.state == "minimized":
                raise zendriver.core.connection.ProtocolException("restore first")
            self.state = want
        return {}


def make_tab(window: FakeChromeWindow) -> Tab:
    target = cdp.target.TargetInfo(
        target_id=cdp.target.TargetID("T"), type_="page", title="", url="about:blank",
        attached=True, can_access_opener=False,
    )
    tab = Tab("ws://127.0.0.1:9/devtools/page/T", target=target)

    async def send(cdp_obj, _is_update=False):
        request = next(cdp_obj)
        response = window.handle(request["method"], request.get("params", {}))
        try:
            cdp_obj.send(response)
        except StopIteration as e:
            return e.value

    tab.send = send  # instance attribute, Connection's class can't be patched
    return tab


@pytest.mark.parametrize("first", ["maximize", "minimize", "fullscreen"])
async def test_set_window_size_from_non_normal_state_applies_bounds(first: str) -> None:
    print("zendriver imported from", zendriver.__file__)
    window = FakeChromeWindow()
    tab = make_tab(window)
    await getattr(tab, first)()
    await tab.set_window_size(200, 100, 900, 700)
    _, b = await tab.get_window()
    assert (b.window_state, b.left, b.top, b.width, b.height) == (
        cdp.browser.WindowState.NORMAL, 200, 100, 900, 700)


@pytest.mark.parametrize("state", ["maximize", "minimize", "fullscreen"])
async def test_non_normal_state_keeps_restore_geometry(state: str) -> None:
    window = FakeChromeWindow()
    tab = make_tab(window)
    await tab.set_window_size(100, 50, 800, 600)
    await getattr(tab, state)()
    await tab.medimize() if False else None
    # restore the way a user / raw cdp does: no geometry
    window.handle("Browser.setWindowBounds", {"windowId": 1, "bounds": {"windowState": "normal"}})
    _, b = await tab.get_window()
    assert (b.left, b.top, b.width, b.height) == (100, 50, 800, 600)


async def test_state_switch_between_non_normal_states() -> None:
    window = FakeChromeWindow()
    tab = make_tab(window)
    await tab.minimize()
    await tab.maximize()
    assert window.state == "maximized"
    await tab.fullscreen()
    assert window.state == "fullscreen"
    await tab.minimize()
    assert window.state == "minimized"


# ---- real chromium ----
@pytest.fixture
async def browser():
    b = await zendriver.start(headless=True)
    try:
        yield b
    finally:
        await b.stop()


async def test_chrome_window_bounds(browser) -> None:
    tab = browser.main_tab
    for st in ["maximize", "minimize", "fullscreen"]:
        await tab.set_window_size(10, 10, 700, 500)
        await getattr(tab, st)()
        await tab.set_window_size(200, 100, 900, 700)
        _, b = await tab.get_window()
        assert (b.window_state, b.left, b.top, b.width, b.height) == (
            cdp.browser.WindowState.NORMAL, 200, 100, 900, 700), st
    await tab.set_window_size(100, 50, 800, 600)
    await tab.maximize()
    wid, b = await tab.get_window()
    assert b.window_state == cdp.browser.WindowState.MAXIMIZED
    await tab.send(cdp.browser.set_window_bounds(
        wid, cdp.browser.Bounds(window_state=cdp.browser.WindowState.NORMAL)))
    _, b = await tab.get_window()
    assert (b.left, b.top, b.width, b.height) == (100, 50, 800, 600)
    # transitions between non-normal states still work
    await tab.minimize(); await tab.maximize(); await tab.fullscreen(); await tab.minimize()
    _, b = await tab.get_window()
    assert b.window_state == cdp.browser.WindowState.MINIMIZED
    await tab.medimize()
    _, b = await tab.get_window()
    assert b.window_state == cdp.browser.WindowState.NORMAL
