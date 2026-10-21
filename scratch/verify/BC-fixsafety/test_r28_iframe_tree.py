"""R28: tree helpers must descend into same-origin iframe content documents."""

from __future__ import annotations

import pytest

import zendriver as zd
from fakedom import cdp, link, make_node, make_tab

print("zendriver imported from", zd.__file__)


def build_doc(data_v: str) -> tuple[cdp.dom.Node, cdp.dom.Node]:
    """#document > HTML > BODY > IFRAME[content_document: #document > HTML > BODY > DIV#box > P#inner > #text]"""
    text = make_node(10, "#text", node_value="hello same origin")
    p = make_node(9, "P", children=[text], attributes=["id", "inner", "data-v", data_v])
    div = make_node(8, "DIV", children=[p], attributes=["id", "box"])
    ibody = make_node(7, "BODY", children=[div])
    ihtml = make_node(6, "HTML", children=[ibody])
    idoc = make_node(5, "#document", children=[ihtml])
    iframe = make_node(4, "IFRAME", content_document=idoc, attributes=["id", "fr"])
    body = make_node(3, "BODY", children=[iframe])
    html = make_node(2, "HTML", children=[body])
    doc = link(make_node(1, "#document", children=[html]))
    return doc, p


def test_print_import() -> None:
    print("zendriver imported from", zd.__file__)


async def test_update_finds_element_inside_same_origin_iframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_doc, old_p = build_doc("1")
    new_doc, _ = build_doc("2")
    tab, sent = make_tab(monkeypatch, {"DOM.getDocument": lambda params: new_doc})

    elem = zd.Element(old_p, tab, old_doc)
    await elem.update()

    assert elem.get("data-v") == "2"
    assert elem.parent is not None
    assert elem.parent.get("id") == "box"


async def test_remove_from_dom_removes_element_inside_same_origin_iframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc, p = build_doc("1")
    tab, sent = make_tab(monkeypatch, {"DOM.getDocument": lambda params: doc})

    elem = zd.Element(p, tab, doc)
    await elem.remove_from_dom()

    removed = [c["params"]["nodeId"] for c in sent if c["method"] == "DOM.removeNode"]
    assert removed == [p.node_id]


async def test_element_query_inside_same_origin_iframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # every getDocument returns fresh node ids (offset), like Chromium does
    generation = {"n": 0}
    docs: dict[int, cdp.dom.Node] = {}

    def get_document(params: dict) -> cdp.dom.Node:
        generation["n"] += 1
        doc, _ = build_doc("1")
        offset = 100 * generation["n"]

        def shift(n: cdp.dom.Node) -> None:
            n.node_id = cdp.dom.NodeId(n.node_id + offset)
            if n.parent_id is not None:
                n.parent_id = cdp.dom.NodeId(n.parent_id + offset)
            for c in n.children or []:
                shift(c)
            if n.content_document is not None:
                shift(n.content_document)

        shift(doc)
        docs[generation["n"]] = doc
        return doc

    def query_selector(params: dict) -> object:
        valid = {
            int(n) for n in range(100 * generation["n"], 100 * generation["n"] + 100)
        }
        if params["nodeId"] not in valid:
            from fakedom import protocol_error

            return protocol_error("Could not find node with given id")
        # #inner > #text has no element children; query 'P' from DIV#box
        return cdp.dom.NodeId(9 + 100 * generation["n"])

    tab, sent = make_tab(
        monkeypatch,
        {"DOM.getDocument": get_document, "DOM.querySelector": query_selector},
    )
    doc0, p0 = build_doc("1")
    div0 = doc0.children[0].children[0].children[0].content_document.children[0].children[0].children[0]  # type: ignore[index,union-attr]
    box = zd.Element(div0, tab, doc0)

    found = await box.query_selector("p")

    assert found is not None
    assert found.get("id") == "inner"


async def test_find_elements_by_text_in_same_origin_iframe_returns_enclosing_element(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc, p = build_doc("1")
    text = p.children[0]  # type: ignore[index]
    tab, sent = make_tab(
        monkeypatch,
        {
            "DOM.getDocument": lambda params: doc,
            "DOM.performSearch": lambda params: ("s1", 1),
            "DOM.getSearchResults": lambda params: [text.node_id],
            # Chromium describes the node without any tree context
            "DOM.describeNode": lambda params: make_node(
                10, "#text", node_value="hello same origin"
            ),
        },
    )

    items = await tab.find_elements_by_text("hello same origin")

    assert items, items
    assert all(item.node_type == 1 for item in items), [
        (i.node_name, i.node_type) for i in items
    ]


async def test_element_text_does_not_descend_into_iframes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # guard: textContent-like semantics must not pick up text from an iframe document
    tail = make_node(20, "#text", node_value="tail")
    inside = make_node(21, "#text", node_value="inside")
    ip = make_node(22, "P", children=[inside])
    idoc = make_node(23, "#document", children=[ip])
    iframe = make_node(24, "IFRAME", content_document=idoc)
    div = link(make_node(25, "DIV", children=[iframe, tail]))
    tab, _ = make_tab(monkeypatch, {})
    assert zd.Element(div, tab, div).text == "tail"
