import copy
import warnings

import pytest

import zendriver
from zendriver import cdp
from zendriver.core.element import Element

print("R34 test imports zendriver from", zendriver.__file__)


def make_node(attributes):
    return cdp.dom.Node(
        node_id=cdp.dom.NodeId(1),
        backend_node_id=cdp.dom.BackendNodeId(2),
        node_type=1,
        node_name="DIV",
        local_name="div",
        node_value="",
        attributes=attributes,
    )


class FakeTab:
    def __init__(self):
        self.sent = []

    async def send(self, cmd):
        self.sent.append(next(cmd)["method"])
        try:
            cmd.send({})
        except StopIteration as e:
            return e.value


def test_get_class_attribute():
    el = Element(make_node(["id", "a", "class", "btn primary"]), FakeTab())
    assert el.get("class") == "btn primary"
    assert el["class"] == "btn primary"
    assert el.get("class_") == "btn primary"  # still works for old callers
    assert repr(el) == '<div id="a" class="btn primary"></div>'


def test_tree_setter_is_used():
    el = Element(make_node(["id", "a"]), FakeTab())
    doc = make_node(["id", "doc"])
    el.tree = doc
    assert el.tree is doc
    assert "tree" not in el.attrs
    # other names are still forwarded to the html attributes
    el.href = "#x"
    assert el.attrs["href"] == "#x"


@pytest.mark.parametrize("op", [copy.copy, copy.deepcopy])
def test_copy_does_not_recurse(op):
    el = Element(make_node(["id", "a", "class", "c"]), FakeTab())
    dup = op(el)
    assert dup.get("id") == "a"
    assert dup == el


async def test_highlight_overlay_does_not_warn():
    el = Element(make_node(["id", "a"]), FakeTab())
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        await el.highlight_overlay()
        assert el.tab.sent == ["DOM.enable", "Overlay.enable", "Overlay.highlightNode"]
        await el.highlight_overlay()
        assert el.tab.sent[-1] == "Overlay.disable"


def test_deprecated_attribute_access_still_works_and_warns():
    el = Element(make_node(["id", "a", "href", "#"]), FakeTab())
    with pytest.warns(DeprecationWarning):
        assert el.href == "#"
    with pytest.warns(DeprecationWarning):
        assert el.missing is None
    assert not hasattr(el, "_missing")
