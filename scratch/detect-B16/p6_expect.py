import asyncio, threading, http.server, socketserver, gc, logging
import zendriver as zd

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/data"):
            body = ("payload for " + self.path).encode()
            ctype = "text/plain"
        else:
            body = b"<html><body><script>for (let i=0;i<5;i++) fetch('/data?n='+i);</script></body></html>"
            ctype = "text/html"
        self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]

errors = []
async def main():
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, c: errors.append(repr(c.get("exception"))))
    b = await zd.start(headless=True)
    tab = b.main_tab
    mismatches = 0
    for trial in range(5):
        async with tab.expect_request(r".*/data\?n=.*") as exp:
            await tab.get(f"http://127.0.0.1:{port}/page{trial}")
            req = await asyncio.wait_for(exp.value, 10)
            resp = await asyncio.wait_for(exp.response, 10)
            body, _ = await asyncio.wait_for(exp.response_body, 10)
            if req.request.url != resp.url:
                mismatches += 1
            print(f"trial {trial}: request.url={req.request.url[-8:]} response.url={resp.url[-8:]} body={body!r} req_id={req.request_id} exp.request_id={exp.request_id}")
        await asyncio.sleep(0.3)
    gc.collect(); await asyncio.sleep(0.1)
    print("mismatches", mismatches, "loop errors:", errors[:3], len(errors))
    await b.stop()

asyncio.run(asyncio.wait_for(main(), 55))
