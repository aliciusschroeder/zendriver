import asyncio, os, signal, sys
import psutil
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException
print("zendriver from", zd.__file__, "py", sys.version.split()[0])

started = []

async def main():
    # (a) raw Chrome error code, no context manager
    browser = await zd.start(headless=True)
    started.append(browser)
    pid = browser._process_pid
    print("chrome pid", pid)
    tab = browser.main_tab
    try:
        await tab.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
    except ProtocolException as e:
        print("(a) no-cm: ProtocolException code=", e.code, "msg=", (e.message or "").splitlines()[0])
    # (b) same command inside async with browser
    try:
        async with browser:
            await tab.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
    except ProtocolException as e:
        print("(b) async-with-browser: ProtocolException code=", e.code, "args types=", [type(a).__name__ for a in e.args])
    # (c) same inside async with tab (Connection.__aexit__ closes the tab ws)
    try:
        async with tab:
            await tab.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
    except ProtocolException as e:
        print("(c) async-with-tab: ProtocolException code=", e.code)
    # (d) after normal exit of async with browser, is chrome alive?
    async with browser:
        pass
    print("(d) after normal `async with browser` exit: chrome alive =", psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE, "browser.stopped =", browser.stopped)
    await browser.stop()
    started.clear()

    # (e) chrome dies while a command is pending inside async with browser
    browser2 = await zd.start(headless=True)
    started.append(browser2)
    pid2 = browser2._process_pid
    tab2 = await browser2.get("about:blank")
    try:
        async with browser2:
            p = psutil.Process(pid2)
            p.suspend()
            task = asyncio.create_task(tab2.send(cdp.page.get_frame_tree()))
            await asyncio.sleep(0.3)
            p.kill()
            await asyncio.wait_for(task, 15)
    except BaseException as e:
        print("(e) chrome killed mid-command inside async with browser -> caught", type(e).__name__, ":", str(e)[:100], "| __context__:", type(e.__context__).__name__)
    try:
        await asyncio.wait_for(tab2.send(cdp.page.get_frame_tree()), 10)
    except BaseException as e:
        print("(e') same command with no context manager after death ->", type(e).__name__, ":", str(e)[:80])
    await browser2.stop()
    started.clear()

async def outer():
    try:
        await asyncio.wait_for(main(), 90)
    finally:
        for b in started:
            try:
                await b.stop()
            except Exception as e:
                print("cleanup err", e)

asyncio.run(outer())
