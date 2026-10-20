import asyncio, os, signal
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get("about:blank")
    await tab.evaluate("1 + 1")
    pid = browser._process_pid
    os.kill(pid, signal.SIGSTOP)
    t = asyncio.create_task(browser.stop())
    await asyncio.sleep(5)
    print("stop done after 5s:", t.done())
    if not t.done():
        c = t.get_coro()
        while c is not None and hasattr(c, "cr_frame"):
            f = c.cr_frame
            if f is not None:
                print("  ", f.f_code.co_filename.split("zendriver/")[-1], f.f_code.co_name, f.f_lineno)
            c = getattr(c, "cr_await", None)
        print("   awaiting:", c)
    os.kill(pid, signal.SIGCONT)
    try:
        await asyncio.wait_for(t, 20)
        print("stop finished after SIGCONT")
    except BaseException as e:
        print("stop raised after SIGCONT", type(e).__name__, e)

asyncio.run(main())
