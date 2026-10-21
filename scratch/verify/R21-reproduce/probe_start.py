"""End-to-end: zendriver.start() with http_proxy set and no no_proxy."""
import asyncio, os, sys, threading, time, tempfile, shutil, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

mode = sys.argv[1]  # "proxy" or "control"
for k in ["no_proxy", "NO_PROXY", "http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
    os.environ.pop(k, None)

proxy_log = []
class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        proxy_log.append(self.requestline)
        self.send_response(502); self.send_header("Content-Length", "0"); self.end_headers()
    def log_message(self, *a): pass
px = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
threading.Thread(target=px.serve_forever, daemon=True).start()
if mode == "proxy":
    os.environ["http_proxy"] = f"http://127.0.0.1:{px.server_address[1]}"

import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0], "mode", mode, "http_proxy", os.environ.get("http_proxy"))

udd = tempfile.mkdtemp(prefix="r21udd-", dir=os.path.dirname(os.path.abspath(__file__)))

def my_chrome_pids():
    out = subprocess.run(["pgrep", "-f", udd], capture_output=True, text=True).stdout.split()
    return [int(p) for p in out if int(p) != os.getpid()]

async def main():
    t0 = time.monotonic()
    browser = None
    try:
        browser = await asyncio.wait_for(
            zd.start(headless=True, browser_connection_max_tries=3, user_data_dir=udd), 60)
        print(f"start OK after {time.monotonic()-t0:.1f}s; ws={browser.info.webSocketDebuggerUrl}")
        tab = await asyncio.wait_for(browser.get("data:text/html,<p>hi</p>"), 30)
        print("page eval:", await tab.evaluate("document.querySelector('p').textContent"))
    except Exception as e:
        msg = " ".join(str(e).split())
        print(f"start FAILED after {time.monotonic()-t0:.1f}s: {type(e).__name__}: {msg[:120]}")
    finally:
        if browser is not None:
            await browser.stop()
    print("proxy saw:", proxy_log)
    await asyncio.sleep(1)
    left = my_chrome_pids()
    print("leftover chrome pids for my profile:", left)
    for p in left:
        try: os.kill(p, 9)
        except ProcessLookupError: pass

asyncio.run(main())
px.shutdown()
shutil.rmtree(udd, ignore_errors=True)
