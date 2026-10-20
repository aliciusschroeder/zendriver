import asyncio, logging, socket, time
import zendriver as zd
import zendriver.core.util as zutil

logging.basicConfig(level=logging.WARNING)
logging.getLogger("zendriver.core.browser").setLevel(logging.INFO)

async def main():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    # occupy the devtools port so chrome cannot listen on it, but keeps running
    zutil.free_port = lambda: port
    import zendriver.core.browser as zb
    zb.util.free_port = lambda: port
    class Spy(logging.Handler):
        def emit(self, rec):
            if "Browser stderr" in rec.getMessage():
                print("LOGGED:", rec.getMessage()[:300].replace("\n", " | "))
    logging.getLogger("uc.browser").addHandler(Spy()); logging.getLogger("uc.browser").setLevel(logging.INFO)
    for name in list(logging.root.manager.loggerDict):
        if "browser" in name: logging.getLogger(name).addHandler(Spy()); logging.getLogger(name).setLevel(logging.INFO)
    t0 = time.monotonic()
    try:
        await zd.start(headless=True)
    except Exception as e:
        print(f"start failed after {time.monotonic()-t0:.1f}s: {str(e).strip().splitlines()[1]}")

asyncio.run(main())
