import asyncio, sys, threading, http.server, functools, os, gc
import zendriver as zd
from zendriver import cdp

def serve():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=d))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]

async def main():
    port = serve()
    url = f"http://127.0.0.1:{port}/many.html"
    browser = await zd.start(headless=True)
    errors = []
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, ctx: errors.append(repr(ctx.get("exception"))))
    try:
        tab = browser.main_tab
        mismatches = 0
        for trial in range(5):
            await tab.get("about:blank")
            async with tab.expect_request(r".*/pix\d+\.gif") as exp:
                await tab.get(url)
                req = await asyncio.wait_for(exp.value, 5)
                resp = await asyncio.wait_for(exp.response_future, 5)
                ok = req.request_id == resp.request_id
                mismatches += not ok
                print(f"trial {trial}: value.url={req.request.url.rsplit('/',1)[1]} request_id(attr)={exp.request_id} value.request_id={req.request_id} response.url={resp.response.url.rsplit('/',1)[1]} match={ok}")
        gc.collect()
        await asyncio.sleep(0.2)
        print("mismatches:", mismatches, "lost task exceptions:", len(errors), errors[:2])
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
