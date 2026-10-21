"""
real chromium probes of Browser.stop(). usage: probe.py MODE
prints PID/UDD so the driver can check them after the interpreter exits
"""

import asyncio
import gc
import http.server
import os
import signal
import sys
import threading
import time

import psutil

import zendriver as zd
from zendriver.core.proxy import pipe

MODE = sys.argv[1]


def info(*a: object) -> None:
    print(*a, flush=True)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        body = b"<html><body><p id=text>hi</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


async def upstream_proxy(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    # accepts any credentials, forwards plain http requests
    try:
        head = await reader.readuntil(b"\r\n\r\n")
        request_line, *header_lines = head.decode().split("\r\n")[:-2]
        method, target, version = request_line.split(" ")
        import urllib.parse

        url = urllib.parse.urlsplit(target)
        ur, uw = await asyncio.open_connection(url.hostname, url.port)
        headers = [h for h in header_lines if not h.lower().startswith("proxy-")]
        uw.write("\r\n".join([f"{method} {url.path or '/'} {version}", *headers, "", ""]).encode())
        await pipe(reader, writer, ur, uw)
    finally:
        writer.close()


def alive(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


async def main() -> None:
    loop = asyncio.get_running_loop()
    seen: list[str] = []
    default = loop.get_exception_handler()

    def handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
        seen.append(context["message"])
        loop.default_exception_handler(context)

    loop.set_exception_handler(handler)
    info("zendriver", zd.__file__, sys.version.split()[0])
    b = await zd.start(headless=True, sandbox=False)
    pid = b._process_pid
    udd = b.config.user_data_dir
    info("PID", pid)
    info("UDD", udd)
    tab = await b.get("about:blank")
    await tab.evaluate("1")
    t2 = await b.get("about:blank", new_tab=True)
    await t2.evaluate("1")

    if MODE.startswith("proxy"):
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        up = await asyncio.start_server(upstream_proxy, "127.0.0.1", 0)
        up_port = up.sockets[0].getsockname()[1]
        ptab = await b.create_context(
            proxy_server=f"http://user:pass@127.0.0.1:{up_port}",
            proxy_bypass_list=["<-loopback>"],
        )
        await ptab.get(f"http://127.0.0.1:{httpd.server_address[1]}/")
        el = await ptab.select("#text")
        info("proxied page text", el.text)
        fw = b._proxy_forwarders[0]
        info("forwarder client tasks", len(fw._client_tasks))
        if MODE == "proxy_sigstop":
            os.kill(pid, signal.SIGSTOP)
        t0 = time.monotonic()
        task = asyncio.create_task(b.stop())
        done, _ = await asyncio.wait({task}, timeout=60)
        info("stop done", bool(done), "elapsed %.2f" % (time.monotonic() - t0))
        if done:
            info("stop exc", task.exception())
        info("proc alive", alive(pid), "profile exists", os.path.exists(udd))
        up.close()
        httpd.shutdown()
    elif MODE == "sigstop_waitfor":
        os.kill(pid, signal.SIGSTOP)
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(b.stop(), 3)
            info("stop returned")
        except asyncio.TimeoutError:
            info("wait_for(stop(), 3) timed out after %.1f" % (time.monotonic() - t0))
        gc.collect()
        await asyncio.sleep(0.1)
        gc.collect()
    elif MODE == "sigstop_stop":
        os.kill(pid, signal.SIGSTOP)
        t0 = time.monotonic()
        task = asyncio.create_task(b.stop())
        done, _ = await asyncio.wait({task}, timeout=60)
        info("stop done", bool(done), "elapsed %.1f" % (time.monotonic() - t0))
        if done:
            info("stop exc", task.exception())
        info("proc alive", alive(pid), "profile exists", os.path.exists(udd))
    elif MODE == "kill_stop":
        assert b._process is not None
        b._process.kill()
        try:
            await b.stop()
            info("stop OK")
        except BaseException as e:
            info("stop RAISED", repr(e))
        info("_process", b._process, "profile exists", os.path.exists(udd))
    elif MODE == "nostop":
        info("returning without stop()")
    elif MODE == "healthy":
        t0 = time.monotonic()
        await b.stop()
        info("healthy stop elapsed %.2f" % (time.monotonic() - t0))
        info("proc alive", alive(pid), "profile exists", os.path.exists(udd))
    elif MODE == "cancel_then_stop":
        task = asyncio.create_task(b.stop())
        await asyncio.sleep(0.01)
        task.cancel()
        r = await asyncio.gather(task, return_exceptions=True)
        info("first", r)
        t0 = time.monotonic()
        await b.stop()
        info("second stop OK elapsed %.2f" % (time.monotonic() - t0))
        info("proc alive", alive(pid), "profile exists", os.path.exists(udd))
    info("exception handler saw", seen)
    loop.set_exception_handler(default)


asyncio.run(main())
info("after asyncio.run")
