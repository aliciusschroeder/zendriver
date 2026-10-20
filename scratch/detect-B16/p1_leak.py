import asyncio, os, glob, tempfile
import zendriver as zd

T = tempfile.gettempdir()
def count():
    return sorted(glob.glob(os.path.join(T, "uc_*")))

async def main():
    print("tmp:", T, "before:", count())
    # 1. nonexistent executable
    try:
        await zd.start(browser_executable_path="/nonexistent/chrome", headless=True)
    except Exception as e:
        print("exe error:", type(e).__name__)
    print("after bad exe:", count())
    # 2. connect to existing dead port
    try:
        await zd.start(host="127.0.0.1", port=1, headless=True, browser_connection_max_tries=1, browser_connection_timeout=0.05)
    except Exception as e:
        print("connect error:", type(e).__name__, str(e).strip().splitlines()[:3])
    print("after dead connect:", count())

asyncio.run(asyncio.wait_for(main(), 50))
