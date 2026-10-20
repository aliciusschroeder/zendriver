"""R13 regression tests (browser-free): Element.get_position must return None when
there are no content quads, and must not require a node tree."""

import typing

import pytest

import zendriver
from zendriver import cdp
from zendriver.core import element as element_mod

print("zendriver imported from:", zendriver.__file__)


class FakeTab:
    """Drives cdp command generators like Connection.send, answering by method."""

    def __init__(self, quads: list[list[float]]):
        self.quads = quads
        self.sent: list[dict[str, typing.Any]] = []

    async def send(self, cmd: typing.Any) -> typing.Any:
        req = next(cmd)
        self.sent.append(req)
        method = req["method"]
        if method == "DOM.resolveNode":
            resp: dict[str, typing.Any] = {
                "object": {"type": "object", "subtype": "node", "objectId": "obj-1"}
            }
        elif method == "DOM.getContentQuads":
            resp = {"quads": self.quads}
        elif method == "Runtime.callFunctionOn":
            resp = {"result": {"type": "undefined"}}
        elif method == "Input.dispatchMouseEvent":
            resp = {}
        elif method == "Page.captureScreenshot":
            resp = {"data": "AAAA"}
        else:
            raise AssertionError(f"unexpected CDP method {method}")
        try:
            cmd.send(resp)
        except StopIteration as e:
            return e.value
        raise AssertionError("generator did not finish")

    async def sleep(self, t: float = 0.25) -> None:
        return None

    # Tab-level mouse helpers, reduced to the CDP calls they would make
    async def mouse_click(self, x: float, y: float, **kw: typing.Any) -> None:
        for t in ("mousePressed", "mouseReleased"):
            await self.send(cdp.input_.dispatch_mouse_event(t, x, y))

    async def mouse_move(self, x: float, y: float, steps: int = 10) -> None:
        await self.send(
            cdp.input_.dispatch_mouse_event("mouseMoved", x, y)
        )

    def methods(self) -> list[str]:
        return [r["method"] for r in self.sent]

    def js_click_sent(self) -> bool:
        return any(
            r["method"] == "Runtime.callFunctionOn"
            and r["params"]["functionDeclaration"] == "(el) => el.click()"
            for r in self.sent
        )


def make_node(node_id: int = 5, parent_id: int = 4) -> cdp.dom.Node:
    return cdp.dom.Node.from_json(
        {
            "nodeId": node_id,
            "parentId": parent_id,
            "backendNodeId": 50,
            "nodeType": 1,
            "nodeName": "BUTTON",
            "localName": "button",
            "nodeValue": "",
            "childNodeCount": 0,
            "attributes": ["id", "hid", "style", "display:none"],
        }
    )


def make_tree(node: cdp.dom.Node) -> cdp.dom.Node:
    body = cdp.dom.Node.from_json(
        {
            "nodeId": 4,
            "parentId": 1,
            "backendNodeId": 40,
            "nodeType": 1,
            "nodeName": "BODY",
            "localName": "body",
            "nodeValue": "",
            "childNodeCount": 1,
        }
    )
    body.children = [node]
    doc = cdp.dom.Node.from_json(
        {
            "nodeId": 1,
            "backendNodeId": 1,
            "nodeType": 9,
            "nodeName": "#document",
            "localName": "",
            "nodeValue": "",
            "childNodeCount": 1,
        }
    )
    doc.children = [body]
    return doc


QUAD = [[10.0, 20.0, 110.0, 20.0, 110.0, 60.0, 10.0, 60.0]]


def hidden_element() -> tuple[element_mod.Element, FakeTab]:
    node = make_node()
    tab = FakeTab(quads=[])  # what Chrome returns for display:none / detached nodes
    return element_mod.create(node, tab, make_tree(node)), tab  # type: ignore[arg-type]


async def test_get_position_returns_none_without_content_quads() -> None:
    el, _ = hidden_element()
    assert await el.get_position() is None


async def test_click_hidden_element_still_runs_js_click() -> None:
    el, tab = hidden_element()
    await el.click()
    assert tab.js_click_sent(), tab.methods()


async def test_mouse_click_hidden_element_does_not_dispatch() -> None:
    el, tab = hidden_element()
    await el.mouse_click()  # documented: warn and do not click
    assert "Input.dispatchMouseEvent" not in tab.methods()


async def test_mouse_move_and_flash_hidden_element_return() -> None:
    el, tab = hidden_element()
    await el.mouse_move()
    await el.flash()
    assert "Input.dispatchMouseEvent" not in tab.methods()


async def test_screenshot_b64_hidden_element_raises_runtime_error() -> None:
    el, _ = hidden_element()
    with pytest.raises(RuntimeError, match="could not determine position"):
        await el.screenshot_b64()


async def test_click_element_without_tree() -> None:
    # Tab.get_all_linked_sources() creates elements without a tree
    tab = FakeTab(quads=QUAD)
    el = element_mod.create(make_node(), tab)  # type: ignore[arg-type]
    assert el.tree is None
    await el.click()
    assert tab.js_click_sent(), tab.methods()
    await el.click()
    pos = await el.get_position()
    assert pos is not None and pos.center == (60.0, 40.0)


async def test_mouse_click_twice_element_without_tree() -> None:
    tab = FakeTab(quads=QUAD)
    el = element_mod.create(make_node(), tab)  # type: ignore[arg-type]
    await el.mouse_click()
    await el.mouse_click()
    assert tab.methods().count("Input.dispatchMouseEvent") == 4


async def test_visible_element_with_tree_unchanged() -> None:
    node = make_node()
    tab = FakeTab(quads=QUAD)
    el = element_mod.create(node, tab, make_tree(node))  # type: ignore[arg-type]
    assert el.parent is not None
    await el.click()
    assert tab.js_click_sent()
    # flash + click: one resolveNode from click(), cached for get_position
    assert tab.methods().count("DOM.resolveNode") == 1
    pos = await el.get_position()
    assert pos is not None and (pos.width, pos.height) == (100.0, 40.0)
