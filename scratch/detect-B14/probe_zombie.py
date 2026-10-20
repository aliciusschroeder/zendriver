import asyncio, traceback
import zendriver as zd
from zendriver import cdp
from zendriver.core import connection as C
from zendriver.core.connection import ProtocolException

created = []
orig_init = C.Listener.__init__
def init(self, conn):
    if conn.websocket is None and conn._inbox is None:
        created.append("".join(traceback.format_stack(limit=4)[:-1]))
    orig_init(self, conn)
C.Listener.__init__ = init

async def main():
    browser = await zd.start(headless=True)
    errs = []
    asyncio.get_running_loop().set_exception_handler(lambda l, c: errs.append(repr(c.get("exception"))))
    res = {}
    try:
        for i in range(10):
            tid = await browser.connection.send(cdp.target.create_target("about:blank"))
            tab = await browser._get_tab(tid)
            async def ev():
                try:
                    await asyncio.wait_for(tab.evaluate("1"), 3); return "ok"
                except ProtocolException as e: return "protoexc:" + str(e).splitlines()[0]
                except asyncio.TimeoutError: return "HANG"
            async def close():
                await asyncio.sleep(0)
                await browser.connection.send(cdp.target.close_target(tid))
            r, _ = await asyncio.gather(ev(), close())
            res[r] = res.get(r, 0) + 1
        import gc; gc.collect(); await asyncio.sleep(0.3)
        print(res)
        print("listeners created on a detached connection:", len(created))
        if created: print(created[0])
        print("unretrieved task exceptions:", len(errs), errs[:1])
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 100))
