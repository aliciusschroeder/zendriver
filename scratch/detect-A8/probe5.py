import asyncio, copy, pickle, warnings
from zendriver import cdp
from zendriver.core.element import Element
node = cdp.dom.Node(node_id=cdp.dom.NodeId(5), backend_node_id=cdp.dom.BackendNodeId(7), node_type=1,
                    node_name="DIV", local_name="div", node_value="", attributes=["class", "a b", "id", "z"])
class FakeTab:
    async def send(self, cmd):
        print("  send called:", cmd)
        raise RuntimeError("stop here")
el = Element(node, FakeTab())
print("get('class') ->", el.get("class"), "| get('class_') ->", el.get("class_"))
el.tree = "SENTINEL"
print("after el.tree='SENTINEL': el.tree ->", el.tree, "| el.attrs['tree'] ->", el.attrs.get("tree"))
try: hash(el)
except Exception as e: print("hash:", type(e).__name__, e)
try: copy.copy(el); print("copy ok")
except RecursionError: print("copy: RecursionError")
try: pickle.loads(pickle.dumps(el)); print("pickle ok")
except RecursionError: print("pickle: RecursionError")
except Exception as e: print("pickle:", type(e).__name__, str(e)[:80])
warnings.simplefilter("error", DeprecationWarning)
async def hl():
    try:
        await el.highlight_overlay()
    except DeprecationWarning as e:
        print("highlight_overlay under -W error::DeprecationWarning ->", type(e).__name__, e)
    except RuntimeError as e:
        print("highlight_overlay reached send:", e)
asyncio.run(hl())
