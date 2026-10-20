import warnings; warnings.simplefilter("ignore")
import zendriver
from zendriver import cdp
from zendriver.core.element import Element
print("zendriver from", zendriver.__file__)
def mk(attrs, name="DIV"):
    node = cdp.dom.Node(node_id=cdp.dom.NodeId(1), backend_node_id=cdp.dom.BackendNodeId(1), node_type=1,
                        node_name=name, local_name=name.lower(), node_value="", attributes=attrs)
    return Element(node, tab=None)
def t(label, fn):
    try: print("OK  ", label, "->", repr(fn()))
    except Exception as e: print("FAIL", label, "->", type(e).__name__, e)
e1 = mk(["clear", "all"], "BR"); t("['clear','all'] attrs.clear()", lambda: e1.attrs.clear())
e2 = mk(["items", "[1,2]"], "X-LIST"); t("['items','[1,2]'] repr()", lambda: repr(e2))
e3 = mk(["get", "x", "id", "a"]); t("['get','x','id','a'] get('id')", lambda: e3.get("id"))
e4 = mk(["id", "a"]); t("control ['id','a'] get('id'), repr", lambda: (e4.get("id"), repr(e4)))
