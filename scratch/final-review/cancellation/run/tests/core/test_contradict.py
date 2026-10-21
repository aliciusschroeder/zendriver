from typing import Any, cast

import zendriver as zd
from zendriver import ContraDict
from zendriver.core.element import Element


class _FakeTab:
    """Answers the resolve_node command sent by Element.update(_node=...)."""

    async def send(self, cmd: Any) -> zd.cdp.runtime.RemoteObject:
        return zd.cdp.runtime.RemoteObject(type_="object")


def _node(
    node_id: int,
    node_name: str,
    attributes: list[str],
    children: list[zd.cdp.dom.Node] | None = None,
) -> zd.cdp.dom.Node:
    return zd.cdp.dom.Node(
        node_id=zd.cdp.dom.NodeId(node_id),
        backend_node_id=zd.cdp.dom.BackendNodeId(node_id),
        node_type=1,
        node_name=node_name,
        local_name=node_name.lower(),
        node_value="",
        attributes=attributes,
        child_node_count=len(children) if children else 0,
        children=children,
    )


def _element(node: zd.cdp.dom.Node) -> Element:
    return Element(node, cast(zd.Tab, _FakeTab()))


def test_keys_named_like_dict_methods_do_not_shadow_them() -> None:
    cd = ContraDict(
        {
            "clear": "all",
            "items": "3",
            "get": "g",
            "keys": "k",
            "values": "v",
            "update": "u",
            "pop": "p",
            "copy": "c",
            "id": "a",
        },
        silent=True,
    )

    assert cd.get("id") == "a"
    assert dict(cd.items())["items"] == "3"
    assert "keys" in list(cd.keys())
    assert "v" in list(cd.values())
    assert cd.copy()["copy"] == "c"
    cd.update({"new": 1})
    assert cd.pop("new") == 1
    assert cd["clear"] == "all"
    cd.clear()
    assert cd == {}


def test_other_keys_are_still_available_as_attributes() -> None:
    cd = ContraDict(
        {"id": "a", "class": "c", "data-id": "d", "Items": "I"}, silent=True
    )
    cd.title = "t"

    assert cd.id == "a"
    assert getattr(cd, "class") == "c"
    assert getattr(cd, "data-id") == "d"
    assert cd.Items == "I"
    assert cd.title == "t"


async def test_element_with_clear_attribute_can_update() -> None:
    # a legacy <br clear="all">, as found on real pages
    node = _node(1, "BR", ["id", "b", "clear", "all"])
    br = _element(node)

    assert await br.update(_node=node) is br
    assert br.attrs == {"id": "b", "clear": "all"}


def test_element_with_items_attribute_can_be_printed() -> None:
    child = _node(2, "MY-LIST", ["items", "[1,2]"])
    parent = _element(_node(1, "DIV", ["id", "wrap"], [child]))

    assert repr(_element(child)) == '<my-list items="[1,2]"></my-list>'
    assert str(parent) == '<div id="wrap"><my-list items="[1,2]"></my-list></div>'


def test_element_with_get_attribute_can_get_attributes() -> None:
    span = _element(_node(1, "SPAN", ["get", "g", "id", "s"]))

    assert span.get("id") == "s"
    assert span.get("get") == "g"
    assert span["id"] == "s"
