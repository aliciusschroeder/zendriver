"""Control: identical calls with a chromium on PATH connect to the same kind of
already-running endpoint -> the only difference is local-binary autodetection."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_helpers as H  # noqa
import shutil, zendriver
from zendriver.core import util as zutil

async def main():
    print("find_executable() ->", H.find_executable())
    port = await H.launch_remote()
    b = await H.attempt("zd.start(host, port) [chromium on PATH]", lambda: zendriver.start(host="127.0.0.1", port=port))
    if b:
        print("    product:", b.info.Browser, "| _process:", b._process)
        await b.stop()
    port = await H.launch_remote()
    drv = H.FakeUCDriver(port, H.started[-1].pid)
    b = await H.attempt("create_from_undetected_chromedriver [chromium on PATH]", lambda: zutil.create_from_undetected_chromedriver(drv))
    if b:
        print("    product:", b.info.Browser, "| service.stopped:", drv.service.stopped)
        b._process_pid = None  # do not let zendriver touch the pid; we reap it ourselves
        await b.stop()

async def runner():
    try:
        await asyncio.wait_for(main(), 100)
    finally:
        for p in H.started:
            if p.poll() is None:
                p.kill()
            p.wait(); print(f"[reaped own chromium pid={p.pid}]")
        for d in H.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)
asyncio.run(runner())
