import asyncio, sys, os, fcntl, termios, array, ssl, threading, http.server, time
import zendriver as zd
def pending(f):
    buf = array.array('i', [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf); return buf[0]
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
def serve_tls():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Q)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain("cert.pem", "key.pem")
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True, do_handshake_on_connect=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd.server_address[1]
async def main():
    port = serve_tls()
    browser = await zd.start(headless=True)
    p = browser._process
    tab = browser.main_tab
    print("start", pending(p.stderr))
    t0 = time.monotonic()
    i = 0
    while time.monotonic() - t0 < 560:
        i += 1
        try:
            # use fresh hostnames-ish via different ports? just query string
            await asyncio.wait_for(tab.send(zd.cdp.page.navigate(f"https://127.0.0.1:{port}/?{i}")), 10)
        except asyncio.TimeoutError:
            print(f"iteration {i}: navigate TIMEOUT stderr pending {pending(p.stderr)} after {time.monotonic()-t0:.0f}s")
            try:
                await asyncio.wait_for(browser.connection.send(zd.cdp.browser.get_version()), 5); print("browser answers getVersion")
            except asyncio.TimeoutError:
                print("browser does NOT answer getVersion")
            break
        if i % 25 == 0: print(i, pending(p.stderr), f"{time.monotonic()-t0:.0f}s")
    print("final", pending(p.stderr))
    p.kill()
asyncio.run(main())
