"""R24 reproducer: connecting to an already-running browser (host+port) needs a
local browser binary because Config.__init__ always calls find_executable.

Run with PATH that does NOT contain any chrome/chromium/brave/msedge binary.
Chromium is launched here by absolute path (playing the "remote" browser).
"""

import asyncio
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback

import zendriver
import zendriver.core.util as zutil
from zendriver.core.browser import Browser
from zendriver.core.config import Config, find_executable

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
SCRATCH = os.path.dirname(os.path.abspath(__file__))

print("python", sys.version.split()[0])
print("zendriver imported from", zendriver.__file__)
print("PATH =", os.environ["PATH"])


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


started: list[subprocess.Popen] = []
tmpdirs: list[str] = []


async def launch_remote() -> int:
    port = free_port()
    udd = tempfile.mkdtemp(prefix="r24_remote_", dir=SCRATCH)
    tmpdirs.append(udd)
    proc = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--no-sandbox",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={udd}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        # a long TMPDIR breaks chromium's singleton unix socket path
        env={k: v for k, v in os.environ.items() if k != "TMPDIR"},
    )
    started.append(proc)
    # wait for the devtools endpoint without using zendriver
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            await asyncio.sleep(0.1)
    await asyncio.sleep(0.3)
    print(f"[remote chromium pid={proc.pid} port={port}]")
    return port


def short_tb(e: BaseException) -> str:
    frames = traceback.extract_tb(e.__traceback__)
    return " <- ".join(
        f"{os.path.basename(f.filename)}:{f.name}:{f.lineno}" for f in reversed(frames)
    )


async def attempt(label, coro_fn):
    try:
        res = await asyncio.wait_for(coro_fn(), 30)
        print(f"{label}: OK -> {res!r}")
        return res
    except Exception as e:
        print(f"{label}: RAISED {type(e).__name__}: {str(e)[:90]!r}")
        print(f"    raised at: {short_tb(e)}")
        return None


class FakeService:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakeOptions:
    def __init__(self, addr):
        self.debugger_address = addr


class FakeUCDriver:
    """minimal stand-in for undetected_chromedriver.Chrome"""

    def __init__(self, port, pid):
        self.options = FakeOptions(f"127.0.0.1:{port}")
        self.browser_pid = pid
        self.service = FakeService()
        self.user_data_dir = "x"


async def main():
    # 0. sanity: no browser on PATH
    try:
        print("find_executable() ->", find_executable())
    except FileNotFoundError as e:
        print("find_executable(): FileNotFoundError (no local browser, as intended)")

    # 1. pure Config construction with host+port
    try:
        Config(host="127.0.0.1", port=9222)
        print("Config(host, port): OK")
    except Exception as e:
        print(f"Config(host, port): RAISED {type(e).__name__}  at {short_tb(e)}")

    port = await launch_remote()

    # 2. failing calls against a live, reachable devtools endpoint
    await attempt(
        "zd.start(host, port)",
        lambda: zendriver.start(host="127.0.0.1", port=port),
    )
    await attempt(
        "Browser.create(host=, port=)",
        lambda: Browser.create(host="127.0.0.1", port=port),
    )
    drv = FakeUCDriver(port, started[-1].pid)
    await attempt(
        "create_from_undetected_chromedriver(driver)",
        lambda: zutil.create_from_undetected_chromedriver(drv),
    )
    print("    fake driver.service.stopped =", drv.service.stopped)

    # 3. control: bogus browser_executable_path, same endpoint -> connects
    b = await attempt(
        "zd.start(host, port, browser_executable_path='/does/not/exist')",
        lambda: zendriver.start(
            host="127.0.0.1", port=port, browser_executable_path="/does/not/exist"
        ),
    )
    if b is not None:
        ver = await b.connection.send(zendriver.cdp.browser.get_version())
        print("    connected; product =", ver[1], "| tabs =", len(b.tabs))
        print("    b._process =", b._process, "(no local process launched)")
        await b.stop()  # sends Browser.close to the chromium we launched


async def runner():
    try:
        await asyncio.wait_for(main(), 100)
    finally:
        for p in started:
            if p.poll() is None:
                p.kill()
            p.wait()
            print(f"[killed/reaped own chromium pid={p.pid}]")
        for d in tmpdirs:
            shutil.rmtree(d, ignore_errors=True)


asyncio.run(runner())
