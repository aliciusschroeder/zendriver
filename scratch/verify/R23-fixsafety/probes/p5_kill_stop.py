import asyncio, sys, traceback
import zendriver as zd
print("zendriver from", zd.__file__, sys.version.split()[0])
MODE = sys.argv[1]

async def main():
    b = await zd.start(headless=True)
    await b.get("about:blank")
    b._process.kill(); b._process.wait()
    try:
        if MODE == "stop":
            await asyncio.wait_for(b.stop(), 30)
            print("immediate stop after kill OK")
        else:
            await asyncio.wait_for(b.start(), 60)
            print("immediate start after kill OK")
    except Exception as e:
        print("raised", type(e).__name__, e)
        traceback.print_exc(limit=-6)
    finally:
        try:
            await asyncio.wait_for(b.stop(), 30)
        except Exception as e:
            print("final stop raised", type(e).__name__)
        print("process left:", b._process)

asyncio.run(main())
