"""coro.close() on a suspended Browser.start(): what does the handler do?"""

import asyncio
import os
import subprocess
import sys

import zendriver as zd
from zendriver.core import util

procs = []


def fake_start_process(*a, **k):
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    procs.append(p)
    return p


async def never(self):
    return False


util._start_process = fake_start_process
zd.Browser.test_connection = never


async def main():
    from zendriver.core.config import Config

    cfg = Config(browser_executable_path=sys.executable, browser_connection_timeout=0.05,
                 browser_connection_max_tries=1000)
    b = zd.Browser(cfg)
    coro = b.start()
    fut = asyncio.ensure_future(asyncio.sleep(0))
    # drive the coroutine by hand until it suspends in the retry loop
    try:
        coro.send(None)
    except StopIteration:
        pass
    try:
        coro.close()
        print("close(): ok")
    except BaseException as e:
        print("close() raised", type(e).__name__, e)
    await fut
    p = procs[0]
    await asyncio.sleep(0.3)
    print("rc", p.poll(), "registered", len(util.get_registered_instances()),
          "profile_exists", os.path.exists(b.config.user_data_dir))
    if p.poll() is None:
        p.kill()
        p.wait()


asyncio.run(main())
