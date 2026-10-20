import asyncio, threading, http.server, functools, os, shutil
import zendriver as zd
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "site")
WORK = os.path.join(HERE, "work5")

def serve():
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

async def main():
    shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/docs/index.html")
        await tab.wait_for_ready_state("complete")
        ok = os.path.join(WORK, "ok.mhtml")
        await tab.save_snapshot(ok)
        raw = open(ok, "rb").read()
        win = os.path.join(WORK, "win.mhtml")
        open(win, "wb").write(raw.replace(b"\r\n", b"\r\r\n"))  # what text-mode "w" writes on Windows
        for p in (ok, win):
            t = await browser.get("file://" + p)
            await asyncio.sleep(1.5)
            txt = await t.evaluate("document.body ? document.body.innerText.slice(0,60) : null")
            print(os.path.basename(p), "->", repr(txt))
    finally:
        await browser.stop(); srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 100))
