import asyncio, sys, os, socket
sys.path.insert(0, os.path.dirname(__file__))
import zendriver as zd
from zendriver import cdp
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
from common import start_server
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

loop_errors = []

leftover = []
async def pend(aw, t, label, stack=True, cancel=True):
    task = asyncio.ensure_future(aw)
    done, _ = await asyncio.wait({task}, timeout=t)
    if done:
        try:
            r = task.result(); print(f"[{label}] completed: {r!r}"[:250]); return ("ok", r)
        except BaseException as e:
            print(f"[{label}] raised {type(e).__name__}: {e!s}"[:250]); return ("exc", e)
    print(f"[{label}] STILL PENDING after {t}s")
    if stack:
        task.print_stack(file=sys.stdout)
    if not cancel:
        leftover.append(task); return ("pending", None)
    task.cancel()
    try: await task
    except BaseException: pass
    return ("pending", None)

async def a107(browser, base):
    print("\n=== A10.7 expect_request on a self-polling page, no send inside the block")
    tab = await browser.get(base + "/poll_page", new_tab=True)
    await asyncio.sleep(1)
    print("enabled before:", [m.__name__ for m in tab.enabled_domains], [m.__name__ for m in tab.manually_enabled_domains], "handlers:", {k.__name__: len(v) for k, v in tab.handlers.items() if isinstance(k, type)})
    async with tab.expect_request(r".*/poll.*") as r:
        await pend(r.value, 5, "r.value with no send", cancel=False)
        print("request_future:", r.request_future)
        await tab.evaluate("1")
        await pend(asyncio.shield(r.value), 5, "r.value after unrelated evaluate", stack=False)
        print("first (still awaited) task:", leftover[-1])
    await tab.close()

async def a103(browser, base):
    print("\n=== A10.3 timed-out wait cancels the shared future (expect_response)")
    tab = browser.main_tab
    await tab.get(base + "/start")
    async with tab.expect_response(r".*/page1") as exp:
        try:
            await asyncio.wait_for(exp.value, 0.5)
        except asyncio.TimeoutError:
            print("first wait timed out (expected)")
        print("response_future after timeout:", exp.response_future, "cancelling():", asyncio.current_task().cancelling())
        await tab.get(base + "/page1")
        await asyncio.sleep(0.5)
        res = await pend(exp.value, 5, "second await exp.value after the response arrived", stack=False)
        print("current task cancelling():", asyncio.current_task().cancelling())
    print("loop errors:", loop_errors)
    loop_errors.clear()

    print("\n=== A10.3 intercept variant")
    async with tab.intercept("*/page2*", RequestStage.REQUEST, ResourceType.DOCUMENT) as it:
        try:
            await asyncio.wait_for(it.request, 0.5)
        except asyncio.TimeoutError:
            print("first wait on it.request timed out (expected)")
        print("it.response_future after timeout:", it.response_future)
        nav = asyncio.ensure_future(tab.send(cdp.page.navigate(base + "/page2")))
        await asyncio.sleep(1.5)
        await pend(it.continue_request(), 5, "continue_request after the request was paused", stack=False)
    await pend(nav, 10, "navigation after leaving intercept block", stack=False)
    print("loop errors:", loop_errors)
    loop_errors.clear()

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

async def b137(browser, base):
    tab = browser.main_tab
    failed = []
    tab.add_handler(cdp.network.LoadingFailed, lambda ev: failed.append((ev.request_id, ev.error_text, ev.canceled)))
    print("\n=== A10.8/B13.7 response_body when the body fails after headers")
    async with tab.expect_response(r".*/api\.json") as r:
        await tab.get(base + "/broken_page")
        await pend(r.response, 10, "r.response", stack=False)
        await pend(r.response_body, 10, "r.response_body", cancel=False)
        print("loading_finished_future:", r.loading_finished_future, "request_id", r.request_id)
        print("LoadingFailed events:", failed)
        print("page title:", await tab.evaluate("document.title"))
    failed.clear()
    print("\n=== B13.7 expect_response.value when the request fails before any response (connection refused)")
    port = free_port()
    async with tab.expect_response(rf"http://127\.0\.0\.1:{port}/x") as r:
        await tab.evaluate(f"fetch('http://127.0.0.1:{port}/x').catch(e=>{{document.title='err:'+e}})")
        await pend(r.value, 5, "r.value", cancel=False)
        print("request_future done:", r.request_future.done(), "response_future:", r.response_future)
        await asyncio.sleep(0.3)
        print("LoadingFailed events:", failed, "title:", await tab.evaluate("document.title"))
    tab.remove_handlers()

async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: loop_errors.append(repr(ctx.get("exception") or ctx.get("message"))))
    srv, base = start_server()
    browser = await zd.start(headless=True)
    try:
        await a107(browser, base)
        await a103(browser, base)
        await b137(browser, base)
    finally:
        for t in leftover:
            print("leftover task at end:", t._state, t.get_coro().__qualname__)
            t.cancel()
        await browser.stop()
        srv.shutdown()

asyncio.run(main())
