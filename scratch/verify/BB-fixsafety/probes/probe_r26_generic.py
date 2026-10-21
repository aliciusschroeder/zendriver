import asyncio, functools, http.server, os, tempfile, threading, shutil
import zendriver as zd
from zendriver import cdp
print("ZENDRIVER IMPORTED FROM", zd.__file__)
async def main():
    root = tempfile.mkdtemp(dir=os.path.dirname(__file__))
    open(os.path.join(root, "p.html"), "w").write("<html><body>hello body</body></html>")
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    h.log_message = lambda *a, **k: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/p.html"
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        async with tab.expect_response(url) as exp:
            await tab.get(url)
            try:
                body = await asyncio.wait_for(exp.response_body, 10)
                print("response_body OK:", body)
            except Exception as e:
                print("response_body FAILED:", type(e).__name__, str(e).splitlines()[0])
    finally:
        await browser.stop(); httpd.shutdown(); shutil.rmtree(root, ignore_errors=True)
asyncio.run(main())
