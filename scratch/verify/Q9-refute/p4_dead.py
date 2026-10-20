import asyncio, sys
import psutil
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "py", sys.version.split()[0])
started = []
async def main():
    b = await zd.start(headless=True); started.append(b)
    pid = b._process_pid
    tab = await b.get("about:blank")
    # pending browser-level command when chrome dies, inside async with browser
    try:
        async with b:
            p = psutil.Process(pid); p.suspend()
            t = asyncio.create_task(b.connection.send(cdp.browser.get_version()))
            await asyncio.sleep(0.3); p.kill()
            await asyncio.wait_for(t, 15)
    except BaseException as e:
        print("(f) pending browser cmd at chrome death, in async with browser ->", type(e).__name__, ":", str(e)[:90], "| ctx:", type(e.__context__).__name__)
    try:
        async with b:
            await asyncio.wait_for(tab.send(cdp.page.get_frame_tree()), 10)
    except BaseException as e:
        print("(g) new tab cmd after death, in async with browser ->", type(e).__name__, ":", str(e)[:90], "| ctx:", type(e.__context__).__name__)
    try:
        await asyncio.wait_for(b.connection.send(cdp.browser.get_version()), 10)
    except BaseException as e:
        print("(h) new browser cmd after death, no cm ->", type(e).__name__, ":", str(e)[:90])
    await b.stop(); started.clear()
async def outer():
    try:
        await asyncio.wait_for(main(), 90)
    finally:
        for b in started:
            try: await b.stop()
            except Exception as e: print("cleanup err", e)
asyncio.run(outer())
