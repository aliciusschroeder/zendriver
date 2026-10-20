import asyncio, json, sys, time
import websockets
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection

sent = []
class WS:
    def __init__(self): self.q = asyncio.Queue()
    async def send(self, m):
        m = json.loads(m); sent.append((round(time.monotonic() - T0, 2), m["method"]))
        if m["method"] != "Network.enable":
            self.q.put_nowait(json.dumps({"id": m["id"], "result": {}}))
    async def recv(self): return await self.q.get()
    async def close(self): pass

def chain(coro):
    out = []
    while coro is not None:
        f = getattr(coro, "cr_frame", None)
        if f is None:
            out.append(repr(coro)[:60]); break
        out.append(f"{f.f_code.co_name}:{f.f_lineno}")
        coro = coro.cr_await
    return " -> ".join(out)

async def main():
    global T0
    print("zendriver from", zd.__file__, sys.version.split()[0])
    async def connect(*a, **k): return WS()
    websockets.connect = connect
    c = Connection("ws://fake/devtools/browser/x")
    c.add_handler(cdp.network.RequestWillBeSent, lambda e: None)
    T0 = time.monotonic()
    inner = c.send(cdp.target.set_discover_targets(discover=True))
    task = asyncio.ensure_future(asyncio.wait_for(inner, 0.3))
    await asyncio.wait({task}, timeout=2)
    print("done after 2s:", task.done(), "| sent:", sent)
    print("await chain:", chain(inner))
    await c.aclose(); await asyncio.wait({task}, timeout=1)
    print("after aclose:", task.done(), task.exception() if task.done() else None)
asyncio.run(main())
