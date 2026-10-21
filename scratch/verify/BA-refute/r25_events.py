import asyncio, sys, collections
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
async def run(discover):
    cfg = zd.Config(headless=True); cfg.autodiscover_targets = discover
    b = await zd.Browser.create(cfg)
    seen = collections.Counter()
    async def h(ev): seen[type(ev).__name__] += 1
    b.connection.add_handler(cdp.target, h)
    try:
        await b.tabs[0].send(cdp.page.navigate("data:text/html,a"))
        tid = await b.connection.send(cdp.target.create_target("data:text/html,b"))
        await asyncio.sleep(0.5)
        await b.connection.send(cdp.target.close_target(tid))
        await asyncio.sleep(0.5)
        print(f"autodiscover={discover}: target events seen on browser connection: {dict(seen)}")
    finally:
        await b.stop()
async def main():
    await run(False); await run(True)
asyncio.run(main())
