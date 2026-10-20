import zendriver
from zendriver import ContraDict
from zendriver import cdp
from zendriver.core.element import Element
print("zendriver from", zendriver.__file__)

def t(label, fn):
    try:
        r = fn()
        print(f"{label}: OK -> {r!r}")
    except Exception as e:
        print(f"{label}: {type(e).__name__}: {e}")

cd = ContraDict({"clear": "all", "items": "3", "get": "x", "id": "a"}, silent=True)
t("cd.clear()", lambda: cd.copy().clear())
t("cd.items()", lambda: list(cd.items()))
t("cd.get('id')", lambda: cd.get("id"))
t("cd.id", lambda: cd.id)
t("cd['clear']", lambda: cd["clear"])

def node(name, attrs, bid=1, children=None):
    return cdp.dom.Node(node_id=cdp.dom.NodeId(bid), backend_node_id=cdp.dom.BackendNodeId(bid),
        node_type=1, node_name=name, local_name=name.lower(), node_value="", attributes=attrs,
        child_node_count=len(children) if children else 0, children=children)

br = Element(node("BR", ["clear", "all", "id", "b"]), tab=None)
t("br.attrs.clear()", lambda: br.attrs.clear())
ml = Element(node("MY-LIST", ["items", "[1,2]"]), tab=None)
t("repr(my-list)", lambda: repr(ml))
wrap = Element(node("DIV", ["id", "wrap"], 2, [node("MY-LIST", ["items", "[1,2]"], 3)]), tab=None)
t("str(div wrapping my-list)", lambda: str(wrap))
sp = Element(node("SPAN", ["get", "g", "id", "s"]), tab=None)
t("span.get('id')", lambda: sp.get("id"))
t("span['id']", lambda: sp["id"])
import warnings; warnings.simplefilter("ignore")
t("span.id", lambda: sp.id)
