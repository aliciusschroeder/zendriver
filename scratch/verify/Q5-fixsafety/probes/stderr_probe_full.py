import asyncio, logging, socket, sys, time, shutil
import zendriver
import zendriver.core.util as util

class H(logging.Handler):
    def __init__(self):
        super().__init__(); self.msgs = []
    def emit(self, r):
        self.msgs.append(r.getMessage())

async def main():
    print("zendriver from", zendriver.__file__)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    pass  # bound, not listening
    port = s.getsockname()[1]
    util.free_port = lambda: port
    h = H(); logging.getLogger("zendriver").addHandler(h); logging.getLogger("zendriver").setLevel(logging.INFO)
    cfg = zendriver.Config(headless=True, browser_connection_max_tries=2, browser_connection_timeout=0.5)
    t0 = time.time()
    try:
        b = await asyncio.wait_for(zendriver.start(cfg), 60)
        print("unexpectedly started"); await b.stop()
    except Exception as e:
        print("start failed after %.1fs: %s" % (time.time() - t0, str(e).strip().splitlines()[1] if str(e).strip() else repr(e)))
    for m in h.msgs:
        if "stderr" in m:
            print("LOGGED:", m.replace("\n", " | "))
    s.close()
asyncio.run(main())
