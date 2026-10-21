import asyncio, copy, pickle, sys, warnings, subprocess
import zendriver as zd
from zendriver import cdp
from zendriver.core.element import Element, create
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

class FakeTab:
    def __init__(self): self.sent = []
    async def send(self, cmd, *a, **k):
        # drive the generator to capture the method name
        req = next(cmd)
        self.sent.append(req["method"])
        return None

def mk(attrs, node_id=5, bid=7):
    return cdp.dom.Node(node_id=cdp.dom.NodeId(node_id), backend_node_id=cdp.dom.BackendNodeId(bid), node_type=1,
                        node_name="DIV", local_name="div", node_value="", attributes=attrs)

tab = FakeTab()
el = create(mk(["id", "a", "class", "btn primary"]), tab)
print("[A8.12/B16.14] get('class') ->", repr(el.get("class")), "| get('class_') ->", repr(el.get("class_")),
      "| el['class'] ->", repr(el["class"]), "| attrs keys", list(el.attrs.keys()), "| repr", repr(el))

# A8.14 / B16.16
doc = mk(["id", "root"], node_id=1, bid=1)
el2 = create(mk(["id", "a"]), tab)
el2.tree = doc
print("[A8.14/B16.16] after el.tree=doc: el.tree is doc?", el2.tree is doc, "| el._tree", el2._tree, "| 'tree' in attrs:", "tree" in el2.attrs)
print("   repr:", repr(el2)[:120])
try:
    el2.parent
    print("   el.parent ok")
except Exception as e:
    print("   el.parent raised", type(e).__name__, e)
# control: setting a non-underscore attribute whose name[1:] matches something in vars()
el3 = create(mk(["id", "a"]), tab)
el3.x_tab = 1   # key[1:] == '_tab' is in vars -> goes to object attribute instead of attrs
print("   [side check] el.x_tab=1 -> in attrs?", "x_tab" in el3.attrs, "| in vars?", "x_tab" in vars(el3))

# A8.15
for name, fn in [("copy.copy", copy.copy), ("copy.deepcopy", copy.deepcopy), ("pickle", lambda o: pickle.loads(pickle.dumps(o)))]:
    try:
        r = fn(el)
        print(f"[A8.15] {name} ok -> {type(r).__name__}")
    except RecursionError as e:
        print(f"[A8.15] {name} RecursionError")
    except Exception as e:
        print(f"[A8.15] {name} raised {type(e).__name__}: {str(e)[:120]}")

# A8.16
async def hl():
    t = FakeTab(); e = create(mk(["id", "a"]), t)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        await e.highlight_overlay()
        print("[A8.16] default filters: warnings:", [f"{x.category.__name__}: {x.message}" for x in w], "sent", t.sent)
    t2 = FakeTab(); e2 = create(mk(["id", "a"]), t2)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        try:
            await e2.highlight_overlay()
            print("[A8.16] -W error: ok, sent", t2.sent)
        except Exception as ex:
            print("[A8.16] -W error: raised", type(ex).__name__, ex, "| commands sent before failure:", t2.sent)
asyncio.run(hl())
