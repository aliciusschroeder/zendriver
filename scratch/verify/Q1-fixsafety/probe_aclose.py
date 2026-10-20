import asyncio, sys, logging
sys.path.insert(0, sys.argv[1])
import test_q1_listener_robustness as T
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection
logging.getLogger("uc.connection").setLevel(logging.CRITICAL)
async def main():
    async def connect(*a, **k): return T.ScriptedWebSocket(lambda c: [T.reply(c, {})])
    websockets.connect = connect
    conn = Connection("ws://fake/devtools/browser/x")
    task = asyncio.ensure_future(conn.send(cdp.target.get_target_info()))
    await asyncio.wait({task}, timeout=1)
    print("before aclose: done", task.done(), "| mapper", conn.mapper)
    await conn.aclose()
    await asyncio.wait({task}, timeout=2)
    print("after aclose: send finished?", task.done(), (repr(task.exception()) if task.done() else ""))
    task.cancel(); await asyncio.wait({task}, timeout=1)
asyncio.run(main())
