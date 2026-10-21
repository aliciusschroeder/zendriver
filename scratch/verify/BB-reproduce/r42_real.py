import asyncio, sys, os, logging
sys.path.insert(0, os.path.dirname(__file__))
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException
from common import start_server
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

records = []
class Cap(logging.Handler):
    def emit(self, rec):
        records.append(rec.getMessage()[:200])
lg = logging.getLogger("uc.connection"); lg.setLevel(logging.INFO); lg.addHandler(Cap())

async def main():
    srv, base = start_server()
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get(base + "/a")
        print("=== A1.3 NaN param")
        records.clear()
        cmd = cdp.emulation.set_device_metrics_override(width=100, height=100, device_scale_factor=float("nan"), mobile=False)
        task = asyncio.ensure_future(tab.send(cmd))
        done, _ = await asyncio.wait({task}, timeout=4)
        if not done:
            print("send STILL PENDING after 4s; tab.mapper:", list(tab.mapper), "browser mapper:", list(browser.connection.mapper))
            task.print_stack(file=sys.stdout)
            task.cancel()
            try: await task
            except BaseException: pass
        else:
            print("send finished:", task)
        print("log records:", [r for r in records if "error" in r or "parsing" in r][:3])
        print("connection still usable:", await asyncio.wait_for(tab.evaluate("2+2"), 5))
        # mouse_move with inf
        records.clear()
        t2 = asyncio.ensure_future(tab.mouse_move(float("inf"), 10))
        done, _ = await asyncio.wait({t2}, timeout=4)
        print("mouse_move(inf) pending after 4s:", not done)
        if not done:
            t2.cancel()
            try: await t2
            except BaseException: pass
        print("=== A1.8 ProtocolException drops data")
        try:
            await asyncio.wait_for(tab.send(cdp.page.navigate(url=None)), 5)
        except ProtocolException as e:
            print("str(e):", repr(str(e)))
            print("e.args[0]:", e.args[0])
            print("'Failed to deserialize' in str(e):", "Failed to deserialize" in str(e))
    finally:
        await browser.stop()
        srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 60))
