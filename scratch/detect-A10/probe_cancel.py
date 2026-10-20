import asyncio, threading, http.server, os, sys
import zendriver as zd
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_snip.py")).read())
async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: print("LOOP ERR:", repr(ctx.get("exception"))))
    browser = await zd.start(headless=True, browser_connection_timeout=1.0, browser_connection_max_tries=30)
    tab = browser.main_tab
    await tab.get("about:blank")
    async with tab.expect_response(r".*/page1") as exp:
        try:
            await asyncio.wait_for(exp.value, 0.5)   # nothing loaded yet -> times out
        except asyncio.TimeoutError:
            print("first wait timed out (expected)")
        print("response_future state after timeout:", exp.response_future)
        await tab.get(BASE + "/page1")             # now the response arrives
        await asyncio.sleep(1)
        try:
            v = await asyncio.wait_for(exp.value, 5)
            print("second wait ->", v.response.url)
        except asyncio.CancelledError:
            print("second wait raised CancelledError although the response arrived and nothing cancelled this task")
            print("current task cancelling():", asyncio.current_task().cancelling())
    await browser.stop()
asyncio.run(main())
