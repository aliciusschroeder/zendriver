import asyncio, sys
from zendriver import cdp
from zendriver.core.element import Element
class FakeTab:
    async def send(self, cmd): return None
n = cdp.dom.Node(node_id=cdp.dom.NodeId(1), backend_node_id=cdp.dom.BackendNodeId(1), node_type=1, node_name="DIV", local_name="div", node_value="")
asyncio.run(Element(n, FakeTab()).highlight_overlay()); print("done (default warning filters)")
