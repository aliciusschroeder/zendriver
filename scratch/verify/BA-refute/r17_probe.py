import asyncio, time, sys, threading, http.server, socketserver, os, tempfile, shutil
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/slow"):
            time.sleep(5)
            body = b"<title>slow</title>slow"
            self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path.startswith("/204"):
            self.send_response(204); self.end_headers()
        elif self.path.startswith("/dl"):
            body = b"x"*1000
            self.send_response(200); self.send_header("Content-Type","application/zip"); self.send_header("Content-Disposition","attachment; filename=f.zip"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            body = b"<title>page</title>page"
            self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

srv = TS(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f"http://127.0.0.1:{srv.server_address[1]}"

async def timed(label, coro, outer=20):
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(coro, outer)
        print(f"{label}: OK in {time.monotonic()-t:.2f}s -> {r!r}"[:250])
        return r
    except BaseException as e:
        print(f"{label}: {type(e).__name__} after {time.monotonic()-t:.2f}s {e!r}"[:250])
        return None

async def pages(b):
    return [(t.target_id[:6], t.url) for t in await b._get_targets() if t.type_ == "page"]

async def main():
    dldir = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
    b = await zd.start(headless=True)
    try:
        await timed("get(page)", b.get(B + "/page", timeout=3))
        # raw navigate result for 204 and download
        tab0 = b.tabs[0]
        await timed("raw Page.navigate(/204)", tab0.send(cdp.page.navigate(B + "/204")))
        await timed("raw Page.navigate(/dl)", tab0.send(cdp.page.navigate(B + "/dl")))
        await timed("browser.get(/204, timeout=3)", b.get(B + "/204", timeout=3))
        await timed("browser.get(/dl, timeout=3)", b.get(B + "/dl", timeout=3))
        await timed("tab.get(/204)", tab0.get(B + "/204"))
        await timed("tab.get(/dl)", tab0.get(B + "/dl"))
        print("tab0 url now:", await tab0.evaluate("location.href"))
        print("pages before new_tab:", await pages(b))
        n0 = len(b.tabs)
        await timed("browser.get(/slow, new_tab=True, timeout=2)", b.get(B + "/slow", new_tab=True, timeout=2))
        print("pages right after timeout:", await pages(b), "browser.tabs:", len(b.tabs), "(was", n0, ")")
        await asyncio.sleep(5)
        print("pages 5s later:", await pages(b))
        print("browser.tabs urls:", [t.url for t in b.tabs])
        await timed("browser.get(/204, new_tab=True, timeout=2)", b.get(B + "/204", new_tab=True, timeout=2))
        await timed("browser.get(/dl, new_tab=True, timeout=2)", b.get(B + "/dl", new_tab=True, timeout=2))
        await asyncio.sleep(1)
        print("pages at end:", await pages(b))
        print("browser.tabs at end:", [(t.target_id[:6], t.url) for t in b.tabs])
    finally:
        await b.stop()
        shutil.rmtree(dldir, ignore_errors=True)
        srv.shutdown()

asyncio.run(main())
