import asyncio
import http.server
import sys
import threading

import zendriver as zd
from zendriver import cdp
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType

print("zendriver from", zd.__file__, sys.version.split()[0])

PAGES = {
    "/page1": "<html><body>page1</body></html>",
    "/poll": "<html><body><script>setInterval(()=>fetch('/pollreq?'+Date.now()),300)</script></body></html>",
    "/brokenpage": "<html><body><script>fetch('/broken').then(r=>r.text()).catch(e=>console.log('err',e))</script></body></html>",
    "/refusedpage": "<html><body><script>fetch('http://127.0.0.1:1/x').catch(e=>console.log('err',e))</script></body></html>",
}


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/broken":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "100000")
            self.end_headers()
            self.wfile.write(b'{"a": 1234')
            self.wfile.flush()
            self.close_connection = True
            return
        body = PAGES.get(p, "ok").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"

loop_errors = []


async def a10_3(browser):
    print("\n=== A10.3 expect_response: timed-out wait cancels shared future ===")
    tab = await browser.get("about:blank", new_tab=True)
    async with tab.expect_response(r".*/page1") as exp:
        try:
            await asyncio.wait_for(exp.value, 0.5)
        except asyncio.TimeoutError:
            print("first wait timed out (expected)")
        print("response_future after timeout:", exp.response_future)
        await tab.get(BASE + "/page1")
        await asyncio.sleep(0.5)
        try:
            v = await asyncio.wait_for(exp.value, 5)
            print("second wait OK", v.response.status)
        except asyncio.CancelledError:
            print("second wait raised CancelledError; cancelling() =", asyncio.current_task().cancelling())
        except asyncio.TimeoutError:
            print("second wait TimeoutError")
        # documented recovery
    import gc
    gc.collect()
    await asyncio.sleep(0.1)
    print("loop errors so far:", [repr(e.get("exception")) for e in loop_errors])
    await tab.close()


async def a10_3_intercept(browser):
    print("\n=== A10.3 intercept: timed-out wait then continue_request ===")
    tab = await browser.get("about:blank", new_tab=True)
    nav = None
    async with tab.intercept("*/page1*", RequestStage.REQUEST, ResourceType.DOCUMENT) as i:
        try:
            await asyncio.wait_for(i.request, 0.5)
        except asyncio.TimeoutError:
            print("first wait timed out (expected)")
        nav = asyncio.ensure_future(tab.send(cdp.page.navigate(BASE + "/page1?i")))
        await asyncio.sleep(1.0)
        try:
            await asyncio.wait_for(i.continue_request(), 5)
            print("continue_request OK")
        except asyncio.CancelledError:
            print("continue_request raised CancelledError; cancelling() =", asyncio.current_task().cancelling())
        print("nav done inside block?", nav.done())
    # leaving the block sends Fetch.disable
    try:
        await asyncio.wait_for(asyncio.shield(nav), 5)
        print("nav finished after leaving block (Fetch.disable released it)")
    except asyncio.TimeoutError:
        print("nav still pending after leaving block")
    await tab.close()


async def a10_7(browser):
    print("\n=== A10.7 expect_request on a self-polling page ===")
    tab = await browser.get("about:blank", new_tab=True)
    await tab.get(BASE + "/poll")
    print("enabled before:", tab.enabled_domains, tab.manually_enabled_domains)
    async with tab.expect_request(r".*/pollreq.*") as r:
        try:
            ev = await asyncio.wait_for(asyncio.shield(r.value), 4)
            print("resolved without send:", ev.request.url)
        except asyncio.TimeoutError:
            print("no request seen after 4s")
        await tab.wait(1)
        print("after tab.wait(1): done?", r.request_future.done())
        await tab.evaluate("1")
        try:
            ev = await asyncio.wait_for(asyncio.shield(r.value), 4)
            print("after unrelated send:", ev.request.url)
        except asyncio.TimeoutError:
            print("still nothing after send")
    await tab.close()


async def b13_7(browser):
    print("\n=== B13.7/A10.8 expect_response on a request that fails after headers ===")
    tab = await browser.get("about:blank", new_tab=True)
    failed = []

    async def lf(ev: cdp.network.LoadingFailed):
        failed.append(ev.error_text)

    tab.add_handler(cdp.network.LoadingFailed, lf)
    async with tab.expect_response(r".*/broken") as exp:
        await tab.get(BASE + "/brokenpage")
        resp = await asyncio.wait_for(exp.response, 10)
        print("response status", resp.status)
        try:
            await asyncio.wait_for(asyncio.shield(exp.response_body), 8)
            print("response_body resolved")
        except asyncio.TimeoutError:
            print("response_body still pending after 8s; LoadingFailed:", failed)
    print("\n--- refused connection ---")
    failed.clear()
    async with tab.expect_response(r".*127\.0\.0\.1:1/x") as exp:
        await tab.get(BASE + "/refusedpage")
        try:
            await asyncio.wait_for(asyncio.shield(exp.value), 5)
            print("value resolved")
        except asyncio.TimeoutError:
            print("value pending after 5s; request_future done:", exp.request_future.done(), "LoadingFailed:", failed)
    tab.remove_handlers()
    await tab.close()


async def main():
    asyncio.get_running_loop().set_exception_handler(lambda l, c: loop_errors.append(c))
    browser = await zd.start(headless=True)
    try:
        for f in (a10_3, a10_3_intercept, a10_7, b13_7):
            try:
                await asyncio.wait_for(f(browser), 60)
            except Exception as e:
                print("CASE ERROR", f.__name__, repr(e))
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
