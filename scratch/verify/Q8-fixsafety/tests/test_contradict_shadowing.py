import warnings

import pytest

import zendriver
from zendriver import ContraDict, cdp
from zendriver.core.element import Element


def test_print_import_path() -> None:
    print("zendriver imported from", zendriver.__file__)


def _node(name: str, attributes: list[str], node_id: int = 1, children=None) -> cdp.dom.Node:
    return cdp.dom.Node(
        node_id=cdp.dom.NodeId(node_id),
        backend_node_id=cdp.dom.BackendNodeId(node_id),
        node_type=1,
        node_name=name,
        local_name=name.lower(),
        node_value="",
        attributes=attributes,
        child_node_count=len(children) if children else 0,
        children=children,
    )


class _FakeTab:
    async def send(self, cmd):  # only resolve_node is sent by update(_node=...)
        return cdp.runtime.RemoteObject(type_="object")


def test_contradict_keys_do_not_shadow_dict_methods() -> None:
    cd = ContraDict(
        {"clear": "all", "items": "3", "get": "x", "keys": "k", "values": "v",
         "update": "u", "pop": "p", "copy": "c", "id": "a"},
        silent=True,
    )
    assert cd.get("id") == "a"
    assert dict(cd.items())["items"] == "3"
    assert "clear" in list(cd.keys())
    assert "v" in list(cd.values())
    assert cd.copy()["copy"] == "c"
    cd.update({"new": 1})
    assert cd["new"] == 1
    assert cd.pop("new") == 1
    # keys that are not class attributes are still reachable as attributes
    assert cd.id == "a"
    assert cd["clear"] == "all"
    cd.clear()
    assert len(cd) == 0


def test_contradict_non_method_keys_still_attribute_accessible() -> None:
    cd = ContraDict({"class": "c", "data-id": "d", "Items": "I", "id": "a"}, silent=True)
    assert getattr(cd, "class") == "c"
    assert getattr(cd, "data-id") == "d"
    assert cd.Items == "I"
    assert cd.id == "a"
    cd.title = "t"
    assert cd.title == "t"
    with pytest.raises(AttributeError):
        cd.does_not_exist


def test_contradict_nested_wrap_with_method_named_key() -> None:
    cd = ContraDict({"get": {"items": {"clear": 1}}}, silent=True)
    inner = cd["get"]
    assert isinstance(inner, ContraDict)
    assert inner.get("items").get("clear") == 1


def test_element_with_clear_attribute_can_update() -> None:
    node = _node("BR", ["clear", "all", "id", "b"])
    br = Element(node, tab=_FakeTab())  # type: ignore[arg-type]
    import asyncio

    asyncio.run(br.update(_node=node))
    assert br.attrs["clear"] == "all"
    assert br.get("clear") == "all"
    assert br["clear"] == "all"


def test_element_with_items_attribute_repr_and_parent_repr() -> None:
    child = _node("MY-LIST", ["items", "[1,2]"], 3)
    wrap = Element(_node("DIV", ["id", "wrap"], 2, [child]), tab=None)  # type: ignore[arg-type]
    assert 'items="[1,2]"' in repr(Element(child, tab=None))  # type: ignore[arg-type]
    assert '<my-list items="[1,2]">' in str(wrap)


def test_element_with_get_attribute_get_and_getitem() -> None:
    span = Element(_node("SPAN", ["get", "g", "id", "s"]), tab=None)  # type: ignore[arg-type]
    assert span.get("id") == "s"
    assert span["id"] == "s"
    assert span.get("get") == "g"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert span.id == "s"
