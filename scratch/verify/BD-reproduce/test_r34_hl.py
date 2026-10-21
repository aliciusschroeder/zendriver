import zendriver as zd
from zendriver import cdp
from zendriver.core.element import create
class FakeTab:
    async def send(self, cmd): next(cmd); return None
async def test_hl():
    print("zendriver from", zd.__file__)
    node = cdp.dom.Node(node_id=cdp.dom.NodeId(5), backend_node_id=cdp.dom.BackendNodeId(7), node_type=1, node_name="DIV", local_name="div", node_value="", attributes=["id","a"])
    e = create(node, FakeTab())
    await e.highlight_overlay()
