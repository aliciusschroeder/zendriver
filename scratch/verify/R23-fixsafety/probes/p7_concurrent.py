import asyncio, sys, warnings
import zendriver as zd
print("zendriver from", zd.__file__)
async def main():
    for scenario in ("after-stop", "after-crash"):
        b = await zd.start(headless=True)
        await b.get("about:blank")
        if scenario == "after-stop":
            await b.stop()
        else:
            b._process.kill(); await asyncio.to_thread(b._process.wait)
        launched = []
        orig = zd.core.util._start_process
        def spy(*a, **k):
            p = orig(*a, **k); launched.append(p); return p
        zd.core.browser.util._start_process = spy
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res = await asyncio.wait_for(asyncio.gather(b.start(), b.start(), return_exceptions=True), 90)
        zd.core.browser.util._start_process = orig
        alive = [p.pid for p in launched if p.poll() is None]
        print(scenario, "results:", [type(r).__name__ for r in res], "launched:", len(launched), "alive:", alive, "b._process alive:", b._process is not None and b._process.poll() is None, "warnings:", len(w))
        try:
            await asyncio.wait_for(b.stop(), 30)
        except Exception as e:
            print("stop raised", type(e).__name__)
        for p in launched:
            if p.poll() is None:
                print("leaked pid", p.pid, "-> killing it (we started it)"); p.kill(); p.wait()
asyncio.run(main())
