import asyncio, pathlib
import zendriver as zd
URL = pathlib.Path("imgs.html").resolve().as_uri()
async def main():
    errors = []
    asyncio.get_running_loop().set_exception_handler(lambda l, ctx: errors.append(repr(ctx.get("exception"))))
    b = await zd.start(headless=True)
    try:
        tab = b.main_tab
        mism = 0
        for trial in range(5):
            async with tab.expect_response(r".*/img\d+\.png") as exp:
                await tab.get(URL + f"?t={trial}")
                await tab.wait_for_ready_state("complete")
                resp = await asyncio.wait_for(exp.value, 5)
                req = await asyncio.wait_for(exp.request, 5)
                same = resp.response.url == req.url
                print(f"trial {trial}: request.url={req.url.rsplit('/',1)[-1]} response.url={resp.response.url.rsplit('/',1)[-1]} match={same}")
                mism += not same
        import gc; gc.collect(); await asyncio.sleep(0.2)
        print("mismatches:", mism, "InvalidStateErrors:", sum('InvalidState' in e for e in errors))
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 100))
