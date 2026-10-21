import asyncio, sys, gc
import zendriver as zd
print("zendriver from", zd.__file__)
errors = []
async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: errors.append(repr(ctx.get("exception"))))
    for i in range(8):
        b = await zd.start(headless=True)
        p = await b.get("about:blank")
        await b.get("about:blank", new_tab=True)
        await b.stop()
        await asyncio.sleep(0.3)
        del b, p
        gc.collect()
        await asyncio.sleep(0.1)
    gc.collect()
asyncio.run(main())
print("unretrieved task exceptions:", len(errors), errors[:2])
