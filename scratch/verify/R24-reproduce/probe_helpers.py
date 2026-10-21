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


