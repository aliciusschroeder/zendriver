import asyncio, gc, os, shutil, sys, logging
import zendriver as zd
CHROME = shutil.which("chromium")
async def main():
    print(sys.version.split()[0], zd.__file__)
    loop = asyncio.get_running_loop()
    msgs = []
    loop.set_exception_handler(lambda l, c: msgs.append(c["message"] + " :: " + repr(c.get("future") or c.get("exception"))[:80]))
    for i in range(5):
        b = await zd.start(headless=True, sandbox=False, browser_executable_path=CHROME)
        await b.get("data:text/html,<p>x</p>")
        r = await asyncio.wait_for(asyncio.gather(b.stop(), b.stop(), return_exceptions=True), 60)
        del b; gc.collect(); await asyncio.sleep(0.1); gc.collect()
        print(f"run {i}: results={r} asyncio errors={msgs}")
        msgs.clear()
asyncio.run(main())
