"""Real headless Chromium: inject one unexpected receive error into the browser
connection (Q1 break), then keep using flat-session tabs (Q1 revival), check
event dispatch counts, `async with tab` (Q9), and Browser.stop (Q3) for leaked
listener tasks."""
import asyncio, sys, logging, collections, os
import zendriver as zd
from zendriver import cdp
from fakews import listener_tasks

print(sys.version.split()[0], zd.__file__)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

def listeners_by_conn():
    c = collections.Counter()
    for t in listener_tasks():
        f = t.get_coro().cr_frame
        if f is not None:
            conn = f.f_locals["self"].connection
            c[str(conn.target_id) if conn.target_id else "browser"] += 1
    return dict(c)

async def main():
    browser = await zd.start(headless=True, sandbox=False, browser_executable_path=os.path.join(os.environ["ZBIN"], "chromium"))
    pid = browser._process_pid
    try:
        tab = await browser.get("about:blank")
        tab2 = await browser.get("about:blank", new_tab=True)
        seen = collections.Counter()
        def on_console(ev):
            seen[ev.args[0].value] += 1
        tab.add_handler(cdp.runtime.ConsoleAPICalled, on_console)
        await tab.evaluate("console.log('warmup')")

        ws = browser.connection.websocket
        orig_recv = ws.recv
        state = {"armed": True}
        async def recv(*a, **k):
            msg = await orig_recv(*a, **k)
            if state["armed"] and "boom" in msg: print("RECV", msg[:160])
            if state["armed"] and '"Runtime.consoleAPICalled"' in msg and "boom" in msg:
                state["armed"] = False
                raise RuntimeError("injected receive error")
            return msg
        ws.recv = recv
        await asyncio.sleep(0.3)  # let the in-flight recv() time out so the patch is used
        try:
            r = await asyncio.wait_for(tab.evaluate("console.log('boom'); 41+1"), 5)
            print("evaluate during error returned", r)
        except Exception as e:
            print("evaluate during error raised", type(e).__name__, e)
        bl = browser.connection.listener
        print("browser listener running after error:", bl.running)
        # keep using the tabs: revival
        for i in range(5):
            r = await asyncio.wait_for(tab.evaluate(f"console.log('m{i}'); {i}"), 5)
        r2 = await asyncio.wait_for(tab2.evaluate("2+2"), 5)
        await asyncio.sleep(0.5)
        print("after revival: evaluate ok, tab2 ->", r2)
        print("console counts:", dict(seen))
        print("live listeners per connection:", listeners_by_conn())

        # Q9: async with tab propagates the original exception and detaches
        class MyErr(Exception):
            def __init__(self, a, b): super().__init__(a, b)
        try:
            async with tab2:
                await tab2.evaluate("1")
                raise MyErr(1, 2)
        except MyErr as e:
            print("async with tab2 propagated", repr(e), "session after:", tab2.session_id)
        # tab2 is reusable afterwards (re-attach)
        print("tab2 after async with:", await asyncio.wait_for(tab2.evaluate("3+3"), 5))
        print("live listeners per connection:", listeners_by_conn())
    finally:
        await asyncio.wait_for(browser.stop(), 60)
    await asyncio.sleep(0.5)
    print("listener tasks alive after stop:", len(listener_tasks()))
    import psutil
    print("process alive after stop:", psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE)
    others = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    print("other tasks alive:", [t.get_coro() for t in others])

asyncio.run(main())
