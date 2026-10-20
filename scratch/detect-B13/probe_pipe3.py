import asyncio, sys, os, fcntl, termios, array, ssl, threading, http.server, time
import zendriver as zd
def pending(f):
    buf = array.array('i', [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf); return buf[0]

def serve_tls():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain("cert.pem", "key.pem")
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd.server_address[1]

async def main():
    port = serve_tls()
    browser = await zd.start(headless=True)
    p = browser._process
    tab = browser.main_tab
    print("start", pending(p.stderr))
    t0 = time.monotonic()
    for i in range(150):
        try:
            await asyncio.wait_for(tab.send(zd.cdp.page.navigate(f"https://127.0.0.1:{port}/?{i}")), 10)
            await asyncio.sleep(0.05)
            await asyncio.wait_for(tab.evaluate("1"), 10)
        except asyncio.TimeoutError:
            print(f"iteration {i}: TIMEOUT stderr pending {pending(p.stderr)} after {time.monotonic()-t0:.0f}s")
            try:
                await asyncio.wait_for(browser.connection.send(zd.cdp.browser.get_version()), 5); print("browser answers getVersion")
            except asyncio.TimeoutError:
                print("browser does NOT answer getVersion")
            break
        if i % 25 == 0: print(i, pending(p.stderr))
    print("final", pending(p.stderr))
    p.kill()
asyncio.run(main())
