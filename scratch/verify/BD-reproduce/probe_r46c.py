import asyncio, os, sys, pathlib, time
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
D = os.path.dirname(os.path.abspath(__file__))
URL = pathlib.Path(D, "r46.html").as_uri()
async def heap(tab):
    await tab.send(cdp.heap_profiler.collect_garbage())
    used, total, *_ = await tab.send(cdp.runtime.get_heap_usage())
    return used
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(URL); await tab.sleep(0.5)
        inp = await tab.select("#inp")
        await inp.apply("(e)=>1")
        h0 = await heap(tab); t0 = time.monotonic()
        N = 8000
        for i in range(N):
            await inp.apply("(e) => 1")
        h1 = await heap(tab)
        print(f"[A8.13] heap used after GC: before={h0:.0f} after {N} apply()={h1:.0f} delta={h1-h0:.0f} bytes ({(h1-h0)/N:.1f} B/call) in {time.monotonic()-t0:.1f}s")
        # control: same number of resolve+call with explicit release
        h2 = await heap(tab)
        for i in range(N):
            ro = await tab.send(cdp.dom.resolve_node(backend_node_id=inp.backend_node_id))
            await tab.send(cdp.runtime.call_function_on("(e)=>1", object_id=ro.object_id, arguments=[cdp.runtime.CallArgument(object_id=ro.object_id)], return_by_value=True))
            await tab.send(cdp.runtime.release_object(ro.object_id))
        h3 = await heap(tab)
        print(f"[A8.13 control] with Runtime.releaseObject: before={h2:.0f} after={h3:.0f} delta={h3-h2:.0f} bytes")
    finally:
        await browser.stop(); print("browser stopped")
asyncio.run(asyncio.wait_for(main(), 110))
