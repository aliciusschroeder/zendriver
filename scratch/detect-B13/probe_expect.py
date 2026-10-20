import asyncio, time, threading, http.server, socket
import zendriver as zd

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/broken"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "100000")
            self.end_headers()
            self.wfile.write(b"0123456789")
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            self.close_connection = True
        else:
            body = b"<html><body>page<script>fetch('/broken').then(r=>r.text()).catch(e=>console.log(e))</script></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        async with tab.expect_response(r".*/broken") as exp:
            await tab.get(base + "/")
            resp = await asyncio.wait_for(exp.value, 10)
            print("got response", resp.response.status, resp.response.url)
            t0 = time.monotonic()
            try:
                body = await asyncio.wait_for(exp.response_body, 10)
                print("body", body)
            except asyncio.TimeoutError:
                print(f"response_body still pending after {time.monotonic()-t0:.1f}s (Network.loadingFailed was ignored)")
        # request that never gets a response
        async with tab.expect_response(r".*:1/never") as exp2:
            await tab.evaluate("fetch('http://127.0.0.1:1/never').catch(()=>{})")
            t0 = time.monotonic()
            try:
                await asyncio.wait_for(exp2.value, 5)
            except asyncio.TimeoutError:
                print(f"expect_response.value still pending after {time.monotonic()-t0:.1f}s; request_future done={exp2.request_future.done()}")
    finally:
        await asyncio.wait_for(browser.stop(), 15)
        srv.shutdown()

asyncio.run(main())
