"""Default zendriver flags: how many stderr bytes does ordinary use produce?"""
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

import zendriver

HERE = os.path.dirname(os.path.abspath(__file__))
print("zendriver from", zendriver.__file__, sys.version.split()[0], flush=True)


def pending(f) -> int:
    buf = array.array("i", [0])
    fcntl.ioctl(f.fileno(), termios.FIONREAD, buf, True)
    return buf[0]


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><body><h1>hi</h1><script>console.error('E'.repeat(300)); throw new Error('boom'.repeat(50))</script></body></html>"
        self.send_response(200 if not self.path.startswith("/404") else 404)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def serve(tls: bool) -> int:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(os.path.join(HERE, "cert.pem"), os.path.join(HERE, "key.pem"))
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


async def main() -> None:
    http_port = serve(False)
    https_port = serve(True)
    b = await zendriver.start(headless=True)
    proc = b._process
    print("udd", b.config.user_data_dir, flush=True)
    await asyncio.sleep(3)
    base = pending(proc.stderr)
    print("after start+3s: stderr %d stdout %d" % (base, pending(proc.stdout)), flush=True)
    tab = b.main_tab

    async def run(label: str, n: int, coro_fn) -> None:
        before = pending(proc.stderr)
        t = time.monotonic()
        for i in range(n):
            try:
                await asyncio.wait_for(coro_fn(i), 15)
            except asyncio.TimeoutError:
                print("  %s #%d TIMEOUT" % (label, i), flush=True)
                break
            except Exception as e:  # noqa
                pass
        await asyncio.sleep(0.5)
        after = pending(proc.stderr)
        print("%-40s n=%d  +%d bytes  (%.0f B/op) %.1fs" % (
            label, n, after - before, (after - before) / n, time.monotonic() - t), flush=True)

    await run("http ok page w/ console.error+throw", 20, lambda i: tab.get(f"http://127.0.0.1:{http_port}/p{i}"))
    await run("http 404", 20, lambda i: tab.get(f"http://127.0.0.1:{http_port}/404/{i}"))
    await run("evaluate console.log 2KB", 20, lambda i: tab.evaluate("console.log('x'.repeat(2000)); 1"))
    await run("connection refused", 10, lambda i: tab.get("http://127.0.0.1:9/"))
    await run("dns failure", 10, lambda i: tab.get(f"http://nonexistent-host-{i}.invalid/"))
    await run("self-signed https", 10, lambda i: tab.get(f"https://127.0.0.1:{https_port}/s{i}"))
    await run("self-signed https same url", 10, lambda i: tab.get(f"https://127.0.0.1:{https_port}/same"))
    await run("new tab + close", 10, lambda i: _newtab(b, i, http_port))
    total = pending(proc.stderr)
    print("total pending %d" % total, flush=True)
    data = os.read(proc.stderr.fileno(), 1 << 20)
    # summarise line sources
    import collections, re
    c = collections.Counter()
    sz = collections.Counter()
    for line in data.decode("utf-8", "replace").splitlines():
        m = re.search(r"\[[^\]]*:(ERROR|WARNING|INFO|VERBOSE\d|FATAL):([^\]]+)\]", line)
        key = (m.group(1) + ":" + m.group(2)) if m else line[:80]
        c[key] += 1
        sz[key] += len(line) + 1
    for k, v in c.most_common(25):
        print("  %4d x %6d B  %s" % (v, sz[k], k), flush=True)
    await asyncio.wait_for(b.stop(), 30)
    print("stopped", flush=True)


async def _newtab(b, i, port):
    t = await b.get(f"http://127.0.0.1:{port}/nt{i}", new_tab=True)
    await t.close()


asyncio.run(main())
