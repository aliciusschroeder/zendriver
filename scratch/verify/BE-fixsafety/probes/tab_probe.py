import asyncio, os, pathlib, shutil, tempfile, threading, functools, http.server, json, sys
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)

def serve(root):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    h.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

async def main():
    root = tempfile.mkdtemp(); work = tempfile.mkdtemp()
    os.chdir(work)
    (pathlib.Path(root)/"docs").mkdir()
    (pathlib.Path(root)/"docs"/"index.html").write_text("""<html><head><link href="style.css" rel=stylesheet></head><body>
<a href="sub/page.html">a</a><img src="images/a.png"><a href="other.html">o</a><a href="../up.html">u</a><a href="/root.html">r</a>
<a href="https://example.org/page#frag">x</a><a href="#top">t</a></body></html>""")
    (pathlib.Path(root)/"docs"/"data.txt").write_text("hello data\n")
    srv = serve(root); base = f"http://127.0.0.1:{srv.server_port}"
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(base + "/docs/index.html")
        await tab.wait_for_ready_state("complete")
        print("get_all_urls:", await tab.get_all_urls())
        print("browser-resolved:", await tab.evaluate("JSON.stringify([...document.querySelectorAll('a,link,img,script')].map(e=>e.href||e.src))"))
        # user agent hints
        print("headless_user_agent set:", browser.headless_user_agent is not None)
        print("brands before:", await tab.evaluate("JSON.stringify(navigator.userAgentData.brands)"), "platform", await tab.evaluate("navigator.userAgentData.platform"))
        await tab.set_user_agent(accept_language="de-DE")
        await tab.reload(); await tab.wait_for_ready_state("complete")
        print("brands after:", await tab.evaluate("JSON.stringify(navigator.userAgentData.brands)"), "platform", repr(await tab.evaluate("navigator.userAgentData.platform")), "lang", await tab.evaluate("navigator.language"))
        # download_file quoting
        dl = pathlib.Path(work)/"dl"
        await tab.set_download_path(dl)
        await tab.download_file(base + "/docs/data.txt", "plain.txt")
        await tab.download_file(base + "/docs/data.txt", "O'Reilly.txt")
        await asyncio.sleep(2)
        print("downloads:", sorted(os.listdir(dl)))
        r = await tab.send(cdp.runtime.evaluate("window.__pwned === 1"))
        await tab.download_file(base + "/docs/data.txt", "x'); window.__pwned=1; ('")
        await asyncio.sleep(0.5)
        print("injection ran:", await tab.evaluate("window.__pwned === 1"))
        # snapshot
        data = await tab.send(cdp.page.capture_snapshot())
        print("snapshot CRLF count:", data.count("\r\n"), "ascii:", data.isascii())
        # webp
        try:
            p = await tab.save_screenshot(format="webp"); print("webp ok", p)
        except Exception as e:
            print("webp EXC", type(e).__name__, e)
        p1 = await tab.save_screenshot(); p2 = await tab.save_screenshot()
        print("auto names same:", p1 == p2, p1, p2, [f for f in os.listdir(work) if f.endswith(".jpg")])
        pdf = await tab.print_to_pdf(pathlib.Path(work)/"s.pdf", transfer_mode="ReturnAsStream")
        print("pdf stream size:", os.path.getsize(pdf))
        pdf = await tab.print_to_pdf(pathlib.Path(work)/"b.pdf")
        print("pdf base64 size:", os.path.getsize(pdf))
    finally:
        await browser.stop()
        srv.shutdown()
        os.chdir("/tmp")
        shutil.rmtree(root, ignore_errors=True); shutil.rmtree(work, ignore_errors=True)

asyncio.run(asyncio.wait_for(main(), 100))
