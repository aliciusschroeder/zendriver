import asyncio, pathlib, shutil, sys, tempfile
import zendriver as zd
print("zendriver from", zd.__file__)
async def main():
    work = pathlib.Path(tempfile.mkdtemp(prefix="lastwins_", dir=sys.argv[1]))
    b = None
    try:
        cfg = zd.Config(headless=True, user_data_dir=work / "p",
                        browser_args=["--window-size=800,600", "--window-size=1000,700", "--window-size=800,600"])
        b = await asyncio.wait_for(zd.start(cfg), 60)
        cmd = [c.decode() for c in pathlib.Path(f"/proc/{b._process_pid}/cmdline").read_bytes().split(b"\0") if c]
        print("window-size flags on cmdline:", [c for c in cmd if c.startswith("--window-size")])
        tab = await b.get("about:blank")
        print("outerWidth:", await tab.evaluate("window.outerWidth"))
    finally:
        if b is not None:
            await b.stop()
        shutil.rmtree(work, ignore_errors=True)
asyncio.run(main())
