"""Default zendriver flags (no logging flags): drive Chrome's own ERROR logging
(TLS handshake failures against a self-signed server) until the stderr pipe is full,
then check whether CDP still answers."""
import array
import asyncio
import fcntl
import http.server
import os
import ssl
import sys
import termios
import threading
import time

import psutil
import zendriver

HERE = os.path.dirname(os.path.abspath(__file__))
print("zendriver from", zendriver.__file__, sys.version.split()[0], flush=True)


def pending(f) -> int:
    buf = array.array("i", [0])
    fcntl.ioctl(f.fileno(), termios.FIONREAD, buf, True)
    return buf[0]


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def serve(tls: bool) -> int:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.handle_error = lambda *a: None
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(os.path.join(HERE, "cert.pem"), os.path.join(HERE, "key.pem"))
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True, do_handshake_on_connect=False)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


def pipe_waiters(root_pid: int):
    out = []
    try:
        procs = [psutil.Process(root_pid)] + psutil.Process(root_pid).children(recursive=True)
    except psutil.Error:
        return out
    for p in procs:
        try:
            for tid in os.listdir(f"/proc/{p.pid}/task"):
                w = open(f"/proc/{p.pid}/task/{tid}/wchan").read()
                if w == "anon_pipe_write":
                    comm = open(f"/proc/{p.pid}/task/{tid}/comm").read().strip()
                    ptype = next((a for a in p.cmdline() if a.startswith("--type=")), "--type=browser")
                    out.append((p.pid, tid, comm, ptype))
        except (OSError, psutil.Error):
            pass
    return out


async def main() -> None:
    https_port = serve(True)
    http_port = serve(False)
    b = await zendriver.start(headless=True)
    proc = b._process
    print("udd", b.config.user_data_dir, "args:", [a for a in b.config() if "log" in a or a.startswith("--v")], flush=True)
    tab = await b.get(f"http://127.0.0.1:{http_port}/")
    js = """(async () => { const ps = []; for (let k=0;k<20;k++) ps.push(fetch('https://127.0.0.1:%d/f'+Math.random()).catch(e=>0));
             await Promise.allSettled(ps); return 1; })()""" % https_port
    t0 = time.monotonic()
    hung = False
    for i in range(200):
        try:
            await asyncio.wait_for(tab.evaluate(js, await_promise=True), 15)
        except asyncio.TimeoutError:
            print("round %d: fetch-batch evaluate TIMEOUT after %.0fs total; stderr pending %d" % (i, time.monotonic() - t0, pending(proc.stderr)), flush=True)
            hung = True
            break
        if i % 10 == 0:
            print("round %d ok; stderr pending %d" % (i, pending(proc.stderr)), flush=True)
    print("blocked writers:", pipe_waiters(proc.pid), flush=True)
    for label, coro in [
        ("evaluate 1+1", lambda: tab.evaluate("1+1")),
        ("Browser.getVersion", lambda: b.connection.send(zendriver.cdp.browser.get_version())),
        ("tab.get http (no TLS)", lambda: tab.get(f"http://127.0.0.1:{http_port}/after")),
    ]:
        try:
            r = await asyncio.wait_for(coro(), 10)
            print("  %s: OK" % label, flush=True)
        except asyncio.TimeoutError:
            print("  %s: TIMEOUT" % label, flush=True)
    print("blocked writers now:", pipe_waiters(proc.pid), flush=True)
    st = asyncio.ensure_future(b.stop())
    done, _ = await asyncio.wait({st}, timeout=25)
    if done:
        print("stop returned:", repr(st.exception()), flush=True)
    else:
        print("stop() still pending after 25s:", flush=True)
        st.print_stack()
        # unwedge by draining so stop() can finish on its own
        n = os.read(proc.stderr.fileno(), 1 << 20)
        print("drained", len(n), flush=True)
        try:
            await asyncio.wait_for(st, 30)
            print("stop finished after drain", flush=True)
        except BaseException as e:
            print("stop after drain:", repr(e), flush=True)
            for c in psutil.Process(proc.pid).children(recursive=True):
                c.kill()
            os.kill(proc.pid, 9)
    print("udd exists:", os.path.exists(b.config.user_data_dir), flush=True)


asyncio.run(main())
