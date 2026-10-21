import asyncio, gc, sys, logging
logging.basicConfig(level=logging.INFO)

async def boom():
    raise RuntimeError("x")

async def main():
    t = asyncio.ensure_future(boom())
    await asyncio.wait({t})
    print(t)
    del t
    gc.collect()
    print("A")
    t = asyncio.ensure_future(boom())
    await asyncio.wait({t})
    del t
    gc.collect()
    print("B")

asyncio.run(main())
