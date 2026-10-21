import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.request

import zendriver as zd
from zendriver.core import util as zutil

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
SCRATCH = os.path.dirname(os.path.abspath(__file__))


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def launch():
    port = free_port()
    udd = tempfile.mkdtemp(prefix="r24udd_", dir=SCRATCH)
    proc = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--no-sandbox",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={udd}",
            "--no-first-run",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc, port, udd


async def wait_devtools(port):
    for _ in range(100):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/version", timeout=1
            ) as r:
                return json.loads(r.read())
        except Exception:
            await asyncio.sleep(0.1)
    raise RuntimeError("devtools never came up")


def kill(proc, udd):
    proc.terminate()
    try:
        proc.wait(5)
    except Exception:
        proc.kill()
        proc.wait()
    shutil.rmtree(udd, ignore_errors=True)


async def main():
    print("python", sys.version.split()[0])
    print("zendriver from", zd.__file__)
    print("PATH has chromium?", shutil.which("chromium"), shutil.which("google-chrome"), shutil.which("chrome"))
    try:
        print("find_executable() ->", zd.find_executable())
    except Exception as e:
        print("find_executable() raised", type(e).__name__, str(e)[:80])

    proc, port, udd = launch()
    try:
        ver = await wait_devtools(port)
        print("[verified] chrome DevTools up on port", port, ver.get("Browser"), "pid", proc.pid)

        # 1. util.start(host, port)
        try:
            b = await asyncio.wait_for(zd.start(host="127.0.0.1", port=port), 30)
            print("1 zd.start(host,port): connected", b.info.Browser)
            await b.connection.aclose()  # do not close remote chrome
        except Exception as e:
            print("1 zd.start(host,port) raised", type(e).__name__, str(e)[:90])

        # 2. Browser.create(host=, port=)
        try:
            b = await asyncio.wait_for(zd.Browser.create(host="127.0.0.1", port=port), 30)
            print("2 Browser.create(host,port): connected", b.info.Browser)
            await b.connection.aclose()
        except Exception as e:
            print("2 Browser.create(host,port) raised", type(e).__name__, str(e)[:90])

        # 3. Config(host=, port=)
        try:
            c = zd.Config(host="127.0.0.1", port=port)
            print("3 Config(host,port) ok", c.browser_executable_path)
        except Exception as e:
            print("3 Config(host,port) raised", type(e).__name__, str(e)[:90])

        # 4. create_from_undetected_chromedriver with a fake driver object
        class _Svc:
            def stop(self):
                pass

        class _Opts:
            debugger_address = f"127.0.0.1:{port}"

        class FakeDriver:
            options = _Opts()
            service = _Svc()
            browser_pid = proc.pid
            user_data_dir = udd

        try:
            b = await asyncio.wait_for(
                zutil.create_from_undetected_chromedriver(FakeDriver()), 30
            )
            print("4 create_from_undetected_chromedriver: connected", b.info.Browser)
            b._process_pid = None
            await b.connection.aclose()
        except Exception as e:
            print("4 create_from_undetected_chromedriver raised", type(e).__name__, str(e)[:90])

        # 5. same call with a bogus executable path
        try:
            b = await asyncio.wait_for(
                zd.start(host="127.0.0.1", port=port, browser_executable_path="/does/not/exist"),
                30,
            )
            print("5 zd.start(host,port,bogus exe): connected", b.info.Browser, "tabs", len(b.tabs))
            t = await asyncio.wait_for(b.get("data:text/html,<title>hi</title>"), 30)
            print("5   navigated, title:", await t.evaluate("document.title"))
            await b.connection.aclose()
        except Exception as e:
            print("5 zd.start(host,port,bogus exe) raised", type(e).__name__, str(e)[:90])

        # 6. Config passed explicitly with a bogus path
        try:
            c = zd.Config(host="127.0.0.1", port=port, browser_executable_path="x")
            b = await asyncio.wait_for(zd.start(c), 30)
            print("6 zd.start(Config(host,port,exe='x')): connected", b.info.Browser)
            await b.connection.aclose()
        except Exception as e:
            print("6 raised", type(e).__name__, str(e)[:90])
    finally:
        kill(proc, udd)
        print("chrome killed, exit", proc.returncode)


asyncio.run(main())
