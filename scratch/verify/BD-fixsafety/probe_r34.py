import asyncio, copy, pickle, sys, warnings
import zendriver
from zendriver import cdp
from zendriver.core.element import Element
print("zendriver from", zendriver.__file__)
def node(attrs):
    return cdp.dom.Node(node_id=cdp.dom.NodeId(1), backend_node_id=cdp.dom.BackendNodeId(2), node_type=1, node_name="DIV", local_name="div", node_value="", attributes=attrs)
class FakeTab:
    def __init__(self): self.sent=[]
    async def send(self, cmd):
        d = next(cmd); self.sent.append(d['method'])
        try: cmd.send({})
        except StopIteration as e: return e.value
el = Element(node(["id","a","class","x y"]), FakeTab())
print("get('class') ->", el.get('class'), "| get('class_') ->", el.get('class_'), "| el['class'] ->", el['class'], "| repr", repr(el))
doc = node(["id","doc"])
el.tree = doc
print("after el.tree=doc: el.tree is doc?", el.tree is doc, "| attrs keys", list(el.attrs.keys()))
for name, fn in [("copy", copy.copy), ("deepcopy", copy.deepcopy), ("pickle", lambda e: pickle.loads(pickle.dumps(e)))]:
    try:
        fn(el); print(name, "OK")
    except BaseException as e:
        print(name, type(e).__name__, str(e)[:80])
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    asyncio.run(el.highlight_overlay())
    print("highlight_overlay warnings:", [str(x.message) for x in w])
with warnings.catch_warnings():
    warnings.simplefilter("error", DeprecationWarning)
    el2 = Element(node(["id","b"]), FakeTab())
    try:
        asyncio.run(el2.highlight_overlay()); print("highlight under -W error OK, sent", el2.tab.sent)
    except BaseException as e:
        print("highlight under -W error:", type(e).__name__, e, "sent", el2.tab.sent)
