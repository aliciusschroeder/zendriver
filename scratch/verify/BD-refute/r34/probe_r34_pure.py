import copy, pickle, sys, warnings, asyncio
import zendriver as zd
from zendriver import cdp
from zendriver.core.element import Element
print("zendriver from", zd.__file__, sys.version.split()[0])

def node(attrs, nid=1, bid=1):
    return cdp.dom.Node(node_id=cdp.dom.NodeId(nid), backend_node_id=cdp.dom.BackendNodeId(bid), node_type=1,
                        node_name="DIV", local_name="div", node_value="", attributes=attrs)

class FakeTab:
    def __init__(self): self.sent = []
    async def send(self, cmd):
        self.sent.append(cmd); 
        try:
            next(cmd)  # get method/params
        except StopIteration: pass
        return None

el = Element(node(["id", "a", "class", "btn primary"]), FakeTab())
print("get('class') ->", el.get("class"), "| get('class_') ->", el.get("class_"), "| el['class'] ->", el["class"], "| repr ->", repr(el))
doc = node(["id", "doc"], 99, 99)
el.tree = doc
print("after el.tree = doc: el.tree ->", el.tree, "| attrs keys", list(el.attrs.keys()), "| _tree", el._tree)
print("repr after:", repr(el)[:120])
try:
    el.parent
except Exception as e:
    print("el.parent ->", type(e).__name__, e)
for name, fn in [("copy", copy.copy), ("deepcopy", copy.deepcopy), ("pickle", lambda x: pickle.loads(pickle.dumps(x)))]:
    try:
        fn(Element(node(["id", "a"]), FakeTab()))
        print(name, "OK")
    except BaseException as e:
        print(name, "->", type(e).__name__, str(e)[:80])
try:
    hash(el); print("hash OK")
except TypeError as e:
    print("hash ->", e)

async def hl(mode):
    e2 = Element(node(["id", "b"]), FakeTab())
    with warnings.catch_warnings(record=True) as w:
        if mode == "error":
            warnings.simplefilter("error", DeprecationWarning)
        elif mode == "always":
            warnings.simplefilter("always")
        try:
            await e2.highlight_overlay()
            print(f"highlight_overlay [{mode}] OK; warnings recorded: {[str(x.message)[:60] for x in w]}; sent {len(e2.tab.sent)} cmds")
        except BaseException as ex:
            print(f"highlight_overlay [{mode}] -> {type(ex).__name__}: {ex}; sent {len(e2.tab.sent)} cmds")
asyncio.run(hl("always"))
asyncio.run(hl("error"))
