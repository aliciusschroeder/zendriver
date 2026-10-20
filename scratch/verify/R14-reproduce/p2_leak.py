import os, sys, glob, tempfile, asyncio, logging
import zendriver as zd
from zendriver.core import util
print("zendriver from", zd.__file__, "py", sys.version.split()[0])
print("root logger level:", logging.getLogger().level, "zendriver logger effective:", logging.getLogger("zendriver.core.browser").getEffectiveLevel())
def uc(): return sorted(os.path.basename(p) for p in glob.glob(os.path.join(tempfile.gettempdir(), "uc_*")))

async def main():
    print("start:", uc())
    # (a) bad executable, 3 times
    for i in range(3):
        try:
            await asyncio.wait_for(zd.start(headless=True, browser_executable_path="/nonexistent/chrome"), 30)
        except FileNotFoundError as e:
            print(f"  attempt {i}: FileNotFoundError")
    print("after 3 bad-exe starts:", uc())
    # Holding the instance and calling stop() too
    b = zd.Browser(zd.Config(headless=True, browser_executable_path="/nonexistent/chrome"))
    print("  instance udd materialized at __init__?", b.config._user_data_dir)
    try:
        await b.start()
    except FileNotFoundError:
        print("  held-instance start: FileNotFoundError; calling stop()")
    await b.stop()
    print("  after stop(): dir exists?", os.path.isdir(b.config._user_data_dir))
    print("after held-instance start+stop:", uc())
    # (b) connect existing to a port with nothing listening
    port = util.free_port()
    before = set(uc())
    try:
        await asyncio.wait_for(zd.start(host="127.0.0.1", port=port, browser_connection_max_tries=2, browser_connection_timeout=0.1, browser_executable_path="/bin/true"), 30)
    except Exception as e:
        print("  connect-existing failed:", type(e).__name__, " ".join(str(e).split())[:60])
    print("new after connect-existing failure:", sorted(set(uc()) - before))

asyncio.run(main())
