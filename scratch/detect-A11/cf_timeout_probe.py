import asyncio, time
import zendriver as zd
from zendriver.core import cloudflare as cf

class FakeInput:
    def __init__(self): self.attrs = {}
    async def update(self): return self
    def __await__(self): return self.update().__await__()

class FakeIframe:
    def __init__(self):
        self.node = zd.cdp.dom.Node(node_id=zd.cdp.dom.NodeId(1), backend_node_id=zd.cdp.dom.BackendNodeId(1), node_type=1, node_name="IFRAME", local_name="iframe", node_value="")
        self.attrs = {}
    async def scroll_into_view(self): pass

box = zd.cdp.dom.BoxModel(content=zd.cdp.dom.Quad([0.0,0.0,100.0,0.0,100.0,50.0,0.0,50.0]), padding=zd.cdp.dom.Quad([]), border=zd.cdp.dom.Quad([]), margin=zd.cdp.dom.Quad([]), width=100, height=50)

async def run(timeout, click_delay):
    async def fake_wait(_tab, _timeout):
        return object(), object(), FakeIframe()
    cf.cf_wait_for_interactive_challenge = fake_wait
    tab = zd.Tab.__new__(zd.Tab)
    async def send(c, _u=False):
        next(c); return box
    async def qs(sel): return FakeInput()   # never gets a value: unsolvable
    clicks = []
    async def click(x, y): clicks.append(time.monotonic())
    object.__setattr__(tab, "send", send); object.__setattr__(tab, "query_selector", qs); object.__setattr__(tab, "mouse_click", click)
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(cf.verify_cf(tab, click_delay=click_delay, timeout=timeout), 60)
    except TimeoutError as e:
        print(f"timeout={timeout} click_delay={click_delay}: TimeoutError after {time.monotonic()-t0:.2f}s, clicks={len(clicks)}")

asyncio.run(run(1, 4))
asyncio.run(run(2, 0.1))
