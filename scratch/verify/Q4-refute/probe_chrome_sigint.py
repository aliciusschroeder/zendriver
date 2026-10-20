"""Verify: does a fully started headless Chrome exit on SIGINT / on closed stdio pipes?"""
import asyncio, os, signal, sys, time, json, pathlib
import zendriver as zd
OUT = pathlib.Path(sys.argv[1])
async def main():
    b = await zd.start(headless=True)
    pid = b._process.pid; udd = str(b.config.user_data_dir)
    OUT.write_text(json.dumps([{"pid": pid, "udd": udd}]))
    await b.get("about:blank")
    t0 = time.perf_counter()
    os.kill(pid, signal.SIGINT)
    for _ in range(40):
        if b._process.poll() is not None: break
        await asyncio.sleep(0.1)
    print(f"chrome rc after SIGINT: {b._process.poll()} in {time.perf_counter()-t0:.2f}s")
    await b.stop()
    print("profile after stop:", os.path.exists(udd))
asyncio.run(main())
