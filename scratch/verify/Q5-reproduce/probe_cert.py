"""Default flags: navigations that hit a TLS certificate error make Chrome log ERROR lines
to stderr; the undrained PIPE eventually fills and Chrome stops answering CDP.

usage: probe_cert.py <max_iter> <how>   how = navigate (raw Page.navigate) | get (tab.get)
"""
import asyncio
import fcntl
import http.server
import os
import signal
import ssl
import struct
import sys
import termios
import threading
import time

import zendriver as zd

HERE = os.path.dirname(os.path.abspath(__file__))
print("zendriver from", zd.__file__, "python", sys.version.split()[0], flush=True)
MAX_ITER = int(sys.argv[1]) if len(sys.argv) > 1 else 10
HOW = sys.argv[2] if len(sys.argv) > 2 else "navigate"


def pending(f):
    return struct.unpack("i", fcntl.ioctl(f.fileno(), termios.FIONREAD, struct.pack("i", 0)))[0]


def wchan(pid):
    try:
        return open(f"/proc/{pid}/wchan").read().strip()
    except Exception as e:
        return repr(e)


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html>ok</html>")

    def log_message(self, *a):
        pass


def serve():
    class S(http.server.ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            pass
    httpd = S(("127.0.0.1", 0), H)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(os.path.join(HERE, "cert.pem"), os.path.join(HERE, "key.pem"))
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True, do_handshake_on_connect=False)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


async def main():
    httpd = serve()
    port = httpd.server_address[1]
    browser = await zd.start(headless=True)
    print("browser args:", [a for a in browser.config() if "logging" in a or "--v=" in a], flush=True)
    proc = browser._process
    pid = proc.pid
    print("pid", pid, "stderr pending after start", pending(proc.stderr), flush=True)
    tab = browser.main_tab
    t0 = time.monotonic()
    hung = False
    for i in range(MAX_ITER):
        url = f"https://127.0.0.1:{port}/p{i}"
        if HOW == "get":
            coro = tab.get(url)
        else:
            coro = tab.send(zd.cdp.page.navigate(url))
        t = asyncio.ensure_future(coro)
        try:
            await asyncio.wait_for(asyncio.shield(t), 15)
        except asyncio.TimeoutError:
            print(f"iteration {i}: navigate TIMEOUT, stderr pending={pending(proc.stderr)} "
                  f"after {time.monotonic()-t0:.0f}s, browser wchan={wchan(pid)}", flush=True)
            t.print_stack(file=sys.stdout)
            hung = True
            t.cancel()
            break
        if HOW != "get":
            await asyncio.sleep(0.2)
        if i < 5 or i % 20 == 0:
            print(f"iteration {i}: ok stderr pending={pending(proc.stderr)} t={time.monotonic()-t0:.0f}s", flush=True)
    else:
        print(f"no hang after {MAX_ITER}; stderr pending={pending(proc.stderr)}", flush=True)
    if hung:
        try:
            await asyncio.wait_for(browser.connection.send(zd.cdp.browser.get_version()), 10)
            print("Browser.getVersion answered", flush=True)
        except asyncio.TimeoutError:
            print("Browser.getVersion TIMEOUT", flush=True)
        # peek at the tail of what Chrome wrote
        data = os.read(proc.stderr.fileno(), 65536)
        print("stderr sample lines:", data.decode(errors="replace").splitlines()[-2:], flush=True)
        try:
            await asyncio.wait_for(tab.evaluate("1+1"), 10)
            print("after draining 64 KiB, evaluate answered again", flush=True)
        except asyncio.TimeoutError:
            print("after draining, evaluate still TIMEOUT", flush=True)
    try:
        await asyncio.wait_for(browser.stop(), 30)
        print("stop ok", flush=True)
    except BaseException as e:
        print("stop failed", type(e).__name__, flush=True)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    httpd.shutdown()


asyncio.run(main())
