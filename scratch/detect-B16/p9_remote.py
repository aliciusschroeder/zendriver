import asyncio, os, sys
import zendriver as zd

async def main():
    port = int(sys.argv[1])
    try:
        b = await zd.start(host="127.0.0.1", port=port)
        print("connected; stopped property says:", b.stopped, "tabs:", len(b.tabs))
        print("temp profile dir created for a remote browser:", b.config.user_data_dir, os.path.isdir(b.config.user_data_dir))
        await b.connection.aclose()
    except Exception as e:
        print("connect to existing browser failed:", type(e).__name__, str(e)[:110])

asyncio.run(asyncio.wait_for(main(), 30))
