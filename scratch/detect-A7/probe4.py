import asyncio, threading, http.server, functools, os, glob, shutil
import zendriver as zd
from zendriver import cdp
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "site")
WORK = os.path.join(HERE, "work4")

def serve():
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

async def main():
    shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
    os.chdir(WORK)
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/intl.html")
        await tab.wait_for_ready_state("complete")
        data = await tab.send(cdp.page.capture_snapshot())
        print("snapshot has CRLF:", "\r\n" in data, "count:", data.count("\r\n"), "non-ascii chars:", sorted(set(c for c in data if ord(c) > 127))[:10])
        # simulate windows text mode
        import io
        buf = io.BytesIO()
        w = io.TextIOWrapper(buf, newline="\r\n", encoding="utf-8")  # what text mode does on windows (newline=None => os.linesep)
        w.write(data); w.flush()
        print("windows-text-mode bytes contain \\r\\r\\n:", b"\r\r\n" in buf.getvalue())
        # print_to_pdf with ReturnAsStream
        try:
            p = await tab.print_to_pdf(os.path.join(WORK, "s.pdf"), transfer_mode="ReturnAsStream")
            print("print_to_pdf ReturnAsStream size:", os.path.getsize(p))
        except Exception as e:
            print("print_to_pdf ReturnAsStream raised", type(e).__name__, e)
        try:
            p = await tab.print_to_pdf(os.path.join(WORK, "nodir", "s.pdf"))
            print("print_to_pdf nodir ok", p)
        except Exception as e:
            print("print_to_pdf nodir raised", type(e).__name__, e)
        # download_file with quote: show exception details ignored
        await tab.set_download_path(os.path.join(WORK, "dl"))
        body = (await tab.query_selector_all("body"))[0]
        await body.update()
        code = "(elem) => { _x('%s') }" % "O'Reilly"
        res = await tab.send(cdp.runtime.call_function_on(code, object_id=body.object_id))
        print("call_function_on with quote -> exception:", res[1] and res[1].exception and res[1].exception.description[:80])
        # local storage roundtrip on page with path
        await tab.set_local_storage({"a": "1", "b": "x y"})
        print("local storage:", await tab.get_local_storage(), "js:", await tab.evaluate("JSON.stringify(Object.assign({}, localStorage))"))
        # save_screenshot auto twice same second
        p1 = await tab.save_screenshot()
        p2 = await tab.save_screenshot()
        print("auto names:", p1, p2, "same:", p1 == p2, "files:", os.listdir(WORK))
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 100))
