"""R36: find_elements_by_text result semantics and select_all(include_frames) partial results."""

from __future__ import annotations

import pytest

import zendriver as zd
from fakedom import cdp, link, make_node, make_tab, protocol_error


def test_print_import() -> None:
    print("zendriver imported from", zd.__file__)


def text_doc() -> cdp.dom.Node:
    login_text = make_node(5, "#text", node_value="Login")
    button = make_node(4, "BUTTON", children=[login_text], attributes=["title", "Login"])
    t1 = make_node(7, "#text", node_value="needle ")
    b = make_node(8, "B", children=[make_node(9, "#text", node_value="x")])
    t2 = make_node(10, "#text", node_value=" needle")
    p = make_node(6, "P", children=[t1, b, t2], attributes=["id", "p1"])
    a_text = make_node(12, "#text", node_value="needle link")
    a = make_node(11, "A", children=[a_text], attributes=["href", "#"])
    body = make_node(3, "BODY", children=[button, p, a])
    html = make_node(2, "HTML", children=[body])
    return link(make_node(1, "#document", children=[html]))


def search_tab(monkeypatch: pytest.MonkeyPatch, ids: list[int]) -> zd.Tab:
    doc = text_doc()
    tab, _ = make_tab(
        monkeypatch,
        {
            "DOM.getDocument": lambda params: doc,
            "DOM.performSearch": lambda params: ("s1", len(ids)),
            "DOM.getSearchResults": lambda params: [cdp.dom.NodeId(i) for i in ids],
        },
    )
    return tab


async def test_find_all_does_not_return_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    # Chromium returns the BUTTON (title attribute match) and its text node;
    # and two text nodes of the same <p>
    tab = search_tab(monkeypatch, [4, 5, 7, 10])
    items = await tab.find_elements_by_text("needle")
    ids = [i.backend_node_id for i in items]
    assert len(ids) == len(set(ids)), [(i.tag, i.backend_node_id) for i in items]


async def test_tag_hint_narrows_results(monkeypatch: pytest.MonkeyPatch) -> None:
    tab = search_tab(monkeypatch, [7, 12])
    items = await tab.find_elements_by_text("needle", tag_hint="a")
    assert [i.tag for i in items] == ["a"]


async def test_find_return_enclosing_element_false_returns_text_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tab = search_tab(monkeypatch, [12])
    el = await tab.find("needle link", return_enclosing_element=False, timeout=0.1)
    assert el.node_type == 3
    el = await tab.find("needle link", timeout=0.1)
    assert el.tag == "a"


def frames_doc() -> cdp.dom.Node:
    inner = make_node(8, "DIV", attributes=["id", "inner"])
    ibody = make_node(7, "BODY", children=[inner])
    idoc = make_node(6, "#document", children=[ibody])
    iframe = make_node(5, "IFRAME", content_document=idoc)
    top = make_node(4, "DIV", attributes=["id", "top"])
    body = make_node(3, "BODY", children=[top, iframe])
    html = make_node(2, "HTML", children=[body])
    return link(make_node(1, "#document", children=[html]))


@pytest.mark.parametrize("stale_document_id", [1, 6])
async def test_select_all_include_frames_retries_stale_documents(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stale_document_id: int,
) -> None:
    doc = frames_doc()
    failed: set[int] = set()

    def query_selector_all(params: dict) -> object:
        node_id = int(params["nodeId"])
        if node_id == stale_document_id and node_id not in failed:
            # the first query against this document hits a stale id
            failed.add(node_id)
            return protocol_error("Could not find node with given id")
        return {1: [cdp.dom.NodeId(4)], 6: [cdp.dom.NodeId(8)]}[node_id]

    tab, _ = make_tab(
        monkeypatch,
        {
            "DOM.getDocument": lambda params: doc,
            "DOM.querySelectorAll": query_selector_all,
        },
    )

    items = await tab.query_selector_all("div", _include_frames=True)

    assert sorted(i.get("id") or "" for i in items) == ["inner", "top"]
    assert "Exception in new content doc ids loop" not in capsys.readouterr().out
