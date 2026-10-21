"""R29: DOM query crashes / swallowed errors / wrong tree for element-scoped results."""

from __future__ import annotations

import pytest

import zendriver as zd
from fakedom import cdp, link, make_node, make_tab, protocol_error
from zendriver.core.connection import ProtocolException


def test_print_import() -> None:
    print("zendriver imported from", zd.__file__)


def simple_doc() -> cdp.dom.Node:
    b = make_node(7, "B", attributes=["id", "bold"])
    p = make_node(6, "P", children=[b], attributes=["id", "deep"])
    inner = make_node(5, "DIV", attributes=["id", "inner"])
    outer = make_node(4, "DIV", children=[inner, p], attributes=["id", "outer"])
    cross = make_node(8, "IFRAME", content_document=None, attributes=["id", "cross"])
    body = make_node(3, "BODY", children=[outer, cross])
    html = make_node(2, "HTML", children=[body])
    return link(make_node(1, "#document", children=[html]))


def find(doc: cdp.dom.Node, node_id: int) -> cdp.dom.Node:
    node = zd.util.filter_recurse(doc, lambda n: n.node_id == node_id)
    assert node is not None
    return node


async def test_find_text_in_shadow_root_inside_same_origin_iframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = make_node(15, "#text", node_value="shadow needle")
    sb = make_node(14, "B", children=[text])
    shadow = make_node(13, "#document-fragment", children=[sb])
    host = make_node(12, "DIV", shadow_roots=[shadow], attributes=["id", "host"])
    ibody = make_node(11, "BODY", children=[host])
    idoc = make_node(10, "#document", children=[ibody])
    iframe = make_node(9, "IFRAME", content_document=idoc)
    body = make_node(3, "BODY", children=[iframe])
    doc = link(make_node(1, "#document", children=[body]))
    tab, _ = make_tab(
        monkeypatch,
        {
            "DOM.getDocument": lambda params: doc,
            "DOM.performSearch": lambda params: ("s1", 0),
        },
    )

    items = await tab.find_elements_by_text("shadow needle")

    assert [i.node_name for i in items] == ["B"]


async def test_query_selector_on_cross_origin_iframe_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc = simple_doc()
    tab, _ = make_tab(monkeypatch, {"DOM.getDocument": lambda params: doc})
    cross = zd.Element(find(doc, 8), tab, doc)

    assert await cross.query_selector_all("p") == []
    assert await cross.query_selector("p") is None


@pytest.mark.parametrize("method", ["query_selector", "query_selector_all"])
async def test_element_scoped_query_raises_on_invalid_selector(
    monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    doc = simple_doc()
    err = lambda params: protocol_error("DOM Error while querying")  # noqa: E731
    tab, sent = make_tab(
        monkeypatch,
        {
            "DOM.getDocument": lambda params: doc,
            "DOM.querySelector": err,
            "DOM.querySelectorAll": err,
        },
    )
    outer = zd.Element(find(doc, 4), tab, doc)

    with pytest.raises(ProtocolException):
        await getattr(outer, method)("a[[")


async def test_element_scoped_query_results_have_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc = simple_doc()
    tab, _ = make_tab(
        monkeypatch,
        {
            "DOM.getDocument": lambda params: doc,
            "DOM.querySelector": lambda params: cdp.dom.NodeId(5),
            "DOM.querySelectorAll": lambda params: [cdp.dom.NodeId(7)],
        },
    )
    outer = zd.Element(find(doc, 4), tab, doc)

    inner = await outer.query_selector("#inner")
    assert inner is not None
    assert isinstance(inner.node, cdp.dom.Node)
    assert inner.parent is not None and inner.parent.get("id") == "outer"

    (bold,) = await outer.query_selector_all("#bold")
    assert isinstance(bold.node, cdp.dom.Node)
    assert bold.parent is not None and bold.parent.get("id") == "deep"
    assert bold.parent.parent is not None
    assert bold.parent.parent.get("id") == "outer"
