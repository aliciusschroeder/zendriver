import asyncio, logging, sys, time, threading
import zendriver as zd
logging.basicConfig(level=logging.WARNING)
logging.getLogger("zendriver.core.browser").setLevel(logging.INFO)

async def main(exe):
    t0 = time.monotonic()
    try:
        await zd.start(browser_executable_path=exe, browser_connection_max_tries=1, browser_connection_timeout=0.25)
    except Exception as e:
        print("start raised", type(e).__name__, "after %.1fs" % (time.monotonic()-t0))
    print("threads alive:", [t.name for t in threading.enumerate() if t is not threading.main_thread()])

asyncio.run(main(sys.argv[1]))
