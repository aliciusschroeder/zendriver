"""Real-Chromium probe for the shared temp profile (A3.6 / A9.3 / B16.5).

usage: p_shared.py repr|config_call|udd_read|none
"""
import asyncio
import glob
import logging
import os
import sys
import tempfile
import time

import zendriver as zd

print("python:", sys.version.split()[0], "| zendriver from:", zd.__file__)
T = tempfile.gettempdir()
MODE = sys.argv[1]

logging.basicConfig(level=logging.WARNING)
logging.getLogger("zendriver.core.browser").setLevel(logging.INFO)
# keep the noisy 'starting ...' line short
class _F(logging.Filter):
    def filter(self, r):
        msg = r.getMessage()
        if msg.startswith("starting"):
            return False
        if "Browser stderr" in msg:
            r.msg = msg[:600]
            r.args = ()
        return True
logging.getLogger("zendriver.core.browser").addFilter(_F())

started = []


def uc():
    return sorted(glob.glob(os.path.join(T, "uc_*")))


async def main():
    config = zd.Config(headless=True)
    if MODE == "repr":
        repr(config)
    elif MODE == "print":
        print(config)
    elif MODE == "config_call":
        config()
    elif MODE == "udd_read":
        _ = config.user_data_dir
    print("template _user_data_dir:", config._user_data_dir, "custom:", config._custom_data_dir)

    b1 = await asyncio.wait_for(zd.start(config), 60)
    started.append(b1)
    print("b1 pid", b1._process_pid, "udd", b1.config.user_data_dir, "custom", b1.config.uses_custom_data_dir)
    print("b1 profile entries:", len(os.listdir(b1.config.user_data_dir)))
    await b1.update_targets()
    print("b1 page tabs before b2:", len(b1.tabs))

    t0 = time.monotonic()
    b2 = None
    try:
        b2 = await asyncio.wait_for(zd.start(config), 60)
        started.append(b2)
        print("b2 STARTED pid", b2._process_pid, "udd", b2.config.user_data_dir)
    except Exception as e:
        print("b2 start failed after %.1fs: %s | Failed to connect: %s" % (time.monotonic() - t0, type(e).__name__, "Failed to connect" in str(e)))

    print("b1 process alive:", b1._process.poll() is None)
    print("b1 profile dir exists:", os.path.isdir(b1.config.user_data_dir))
    await asyncio.sleep(1)
    await b1.update_targets()
    print("b1 page tabs after b2 attempt:", len(b1.tabs), [t.target.url for t in b1.tabs if t.target])

    # does b1 keep working with its profile gone?
    try:
        tab = await asyncio.wait_for(b1.get("http://127.0.0.1:1/never", new_tab=False), 30)
    except Exception as e:
        print("b1.get error:", type(e).__name__, e)
    try:
        tab = b1.main_tab
        r = await asyncio.wait_for(tab.evaluate("1+1"), 10)
        print("b1 evaluate after profile loss:", r)
        await asyncio.wait_for(tab.get("data:text/html,<title>t</title>hello"), 20)
        r = await asyncio.wait_for(tab.evaluate("document.title"), 10)
        print("b1 title after profile loss:", r)
    except Exception as e:
        print("b1 usage error:", type(e).__name__, e)
    print("b1 profile dir exists now:", os.path.isdir(b1.config.user_data_dir),
          "entries:", len(os.listdir(b1.config.user_data_dir)) if os.path.isdir(b1.config.user_data_dir) else None)

    if b2 is not None:
        await b2.stop()
        print("after b2.stop, b1 profile exists:", os.path.isdir(b1.config.user_data_dir), "b1 alive:", b1._process.poll() is None)
    await b1.stop()
    print("after b1.stop, leftover uc_*:", uc())


async def runner():
    try:
        await asyncio.wait_for(main(), 110)
    finally:
        for b in started:
            if b._process is not None and b._process.poll() is None:
                print("safety-stopping", b._process_pid)
                try:
                    await asyncio.wait_for(b.stop(), 15)
                except Exception:
                    b._process.kill()


asyncio.run(runner())
