"""R37: concurrent DOM queries on one tab must not silently return None/[].

The fake peer mimics Chromium: every DOM.getDocument discards all node ids handed
out before (new ids per generation), and a query with an old id fails with
'Could not find node with given id'. Each command yields to the loop, like a
real round trip.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import zendriver as zd
from fakedom import cdp, link, make_node, make_tab, protocol_error

ROWS = 20


def test_print_import() -> None:
    print("zendriver imported from", zd.__file__)


class FakeChromium:
    def __init__(self) -> None:
        self.gen = 0

    def doc(self) -> cdp.dom.Node:
        base = 1000 * self.gen
        rows = []
        for i in range(ROWS):
            td = make_node(base + 100 + 2 * i + 1, "TD", attributes=["id", f"c{i}"])
            td.backend_node_id = cdp.dom.BackendNodeId(100 + 2 * i + 1)
            tr = make_node(base + 100 + 2 * i, "TR", children=[td])
            tr.backend_node_id = cdp.dom.BackendNodeId(100 + 2 * i)
            rows.append(tr)
        table = make_node(base + 4, "TABLE", children=rows)
        p = make_node(base + 5, "P", attributes=["id", "topp"])
        body = make_node(base + 3, "BODY", children=[table, p])
        html = make_node(base + 2, "HTML", children=[body])
        doc = make_node(base + 1, "#document", children=[html])
        for n, b in ((table, 4), (p, 5), (body, 3), (html, 2), (doc, 1)):
            n.backend_node_id = cdp.dom.BackendNodeId(b)
        return link(doc)

    async def get_document(self, params: dict[str, Any]) -> cdp.dom.Node:
        await asyncio.sleep(0)
        self.gen += 1
        return self.doc()

    def _check(self, node_id: int) -> int | None:
        if node_id // 1000 != self.gen:
            return None
        return node_id % 1000

    async def query_selector(self, params: dict[str, Any]) -> Any:
        await asyncio.sleep(0)
        local = self._check(int(params["nodeId"]))
        if local is None:
            return protocol_error("Could not find node with given id")
        base = 1000 * self.gen
        sel = params["selector"]
        if sel == "#topp":
            return cdp.dom.NodeId(base + 5)
        if sel == "td" and 100 <= local < 100 + 2 * ROWS:
            return cdp.dom.NodeId(base + local + 1)
        return cdp.dom.NodeId(0)

    async def query_selector_all(self, params: dict[str, Any]) -> Any:
        r = await self.query_selector(params)
        if isinstance(r, Exception):
            return r
        return [r] if r else []


def chromium_tab(monkeypatch: pytest.MonkeyPatch) -> zd.Tab:
    fake = FakeChromium()
    tab, _ = make_tab(
        monkeypatch,
        {
            "DOM.getDocument": fake.get_document,
            "DOM.querySelector": fake.query_selector,
            "DOM.querySelectorAll": fake.query_selector_all,
        },
    )
    return tab


async def test_concurrent_tab_query_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = chromium_tab(monkeypatch)
    res = await asyncio.wait_for(
        asyncio.gather(*(tab.query_selector("#topp") for _ in range(10))), 10
    )
    assert sum(r is None for r in res) == 0


async def test_concurrent_element_query_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = chromium_tab(monkeypatch)
    doc = await tab.send(cdp.dom.get_document(-1, True))
    table = doc.children[0].children[0].children[0]  # type: ignore[index]
    rows = [zd.Element(tr, tab, doc) for tr in table.children]  # type: ignore[union-attr]
    res = await asyncio.wait_for(
        asyncio.gather(*(r.query_selector("td") for r in rows)), 10
    )
    assert sum(r is None for r in res) == 0
    assert [r.get("id") for r in res] == [f"c{i}" for i in range(ROWS)]  # type: ignore[union-attr]
    assert not [r for r in rows if "__last" in vars(r)]


async def test_stale_element_retry_is_reentrant(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tab.query_selector(sel, stale_element) calls element.update() from inside the
    # query: with a per-tab lock this must not deadlock
    tab = chromium_tab(monkeypatch)
    doc = await tab.send(cdp.dom.get_document(-1, True))
    table = doc.children[0].children[0].children[0]  # type: ignore[index]
    row = zd.Element(table.children[3], tab, doc)  # type: ignore[index]
    await tab.send(cdp.dom.get_document(-1, True))  # invalidates row's node id
    td = await asyncio.wait_for(tab.query_selector("td", row), 5)
    assert td is not None and td.get("id") == "c3"
    assert "__last" not in vars(row)


async def test_cancelled_query_releases_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeChromium()
    gate = asyncio.Event()

    async def slow_get_document(params: dict[str, Any]) -> cdp.dom.Node:
        await gate.wait()
        return await fake.get_document(params)

    tab, _ = make_tab(
        monkeypatch,
        {"DOM.getDocument": slow_get_document, "DOM.querySelector": fake.query_selector},
    )
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(tab.query_selector("#topp"), 0.2)
    gate.set()
    r = await asyncio.wait_for(tab.query_selector("#topp"), 5)
    assert r is not None
