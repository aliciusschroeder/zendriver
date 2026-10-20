import asyncio, inspect, pkgutil, importlib, traceback
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException

async def main():
    browser = await zd.start(headless=True)
    hung = []
    try:
        tab = await browser.get("about:blank")
        await tab.send(cdp.network.set_cookie(name="a", value="b", url="https://example.com", same_site=cdp.network.CookieSameSite.LAX, partition_key=None))
        for modinfo in pkgutil.iter_modules(cdp.__path__):
            mod = importlib.import_module("zendriver.cdp." + modinfo.name)
            for name, fn in inspect.getmembers(mod, inspect.isfunction):
                if fn.__module__ != mod.__name__ or not name.startswith("get_"):
                    continue
                sig = inspect.signature(fn)
                if any(p.default is inspect._empty for p in sig.parameters.values()):
                    continue
                for conn, label in ((tab, "tab"),):
                    try:
                        await asyncio.wait_for(conn.send(fn()), 3)
                    except asyncio.TimeoutError:
                        hung.append(f"{label}:{mod.__name__}.{name}")
                        print("HUNG", label, mod.__name__, name, "listener running:", conn.listener.running, flush=True)
                        if not browser.connection.listener.running:
                            await browser.connection.send(cdp.target.get_targets())
                    except ProtocolException:
                        pass
                    except Exception as e:
                        print("EXC", label, mod.__name__, name, type(e).__name__, e, flush=True)
    finally:
        await browser.stop()
    print("hung:", hung)

asyncio.run(asyncio.wait_for(main(), 280))
