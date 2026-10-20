import asyncio, threading, functools, http.server, socketserver
import zendriver as zd
from zendriver import cdp
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/trunc"):
            self.send_response(200); self.send_header("Content-Type", "text/plain"); self.send_header("Content-Length", "1000"); self.end_headers()
            self.wfile.write(b"0123456789"); self.wfile.flush(); self.close_connection = True; return
        return super().do_GET()
class S(socketserver.ThreadingMixIn, socketserver.TCPServer): daemon_threads = True
srv = S(("127.0.0.1", 0), functools.partial(Q, directory="www"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    b = await zd.start(headless=True)
    try:
        tab = b.main_tab
        failed = []; seen = []; allev = []
        tab.add_handler(cdp.network, lambda e: allev.append((type(e).__name__, getattr(e, "request_id", None))))
        tab.add_handler(cdp.network.ResponseReceived, lambda e: seen.append(("resp", e.response.url[-12:], e.request_id)))
        tab.add_handler(cdp.network.RequestWillBeSent, lambda e: seen.append(("req", e.request.url[-12:], e.request_id)))
        tab.add_handler(cdp.network.LoadingFailed, lambda e: failed.append(e.error_text))
        async with tab.expect_response(r".*/trunc") as r:
            await tab.get(BASE + "/trunc_page.html")
            await asyncio.sleep(3); print("all:", allev); print("seen:", seen, "failed:", failed, "exp.request_id:", r.request_id)
            resp = await asyncio.wait_for(r.value, 5)
            print("response received:", resp.response.status)
            try:
                body = await asyncio.wait_for(r.response_body, 5)
                print("body:", body)
            except TimeoutError:
                print("response_body did not return within 5s; LoadingFailed seen:", failed)
    finally:
        await b.stop(); srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 60))
