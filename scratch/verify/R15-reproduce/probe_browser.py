import asyncio, collections, os, sys, signal
import zendriver
from zendriver import Config, Browser
HERE = os.path.dirname(os.path.abspath(__file__))
print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)

def cmdline(pid):
    with open(f"/proc/{pid}/cmdline", "rb") as f:
        return [a.decode() for a in f.read().split(b"\0") if a]

def dups(args):
    return {a: n for a, n in collections.Counter(args).items() if n > 1}

started = []
import itertools
_n = itertools.count()
def prof():
    d = os.path.join(HERE, "profiles", "p%d" % next(_n)); os.makedirs(d, exist_ok=True); return d

async def k2():
    print("\n=== K2 (real chromium): duplicate / conflicting Config-owned flags in argv ===")
    b = await zendriver.start(headless=True, lang="de-DE", user_data_dir=prof(),
                              browser_args=["--headless=new", "--no-sandbox", "--lang=fr-FR",
                                            "--webrtc-ip-handling-policy=default_public_interface_only"])
    started.append(b)
    argv = cmdline(b._process_pid)
    print("pid", b._process_pid, "duplicates in real argv:", dups(argv))
    print("--lang entries in argv:", [a for a in argv if a.startswith("--lang")])
    print("webrtc entries in argv:", [a for a in argv if a.startswith("--webrtc")])
    tab = await b.get("about:blank")
    print("navigator.language =", await tab.evaluate("navigator.language"),
          "(user passed --lang=fr-FR, Config appended --lang=de-DE; last wins)")
    await b.stop()

async def k3():
    print("\n=== K3 (real chromium): --load-extension appended on every start ===")
    cfg = Config(headless=True, user_data_dir=prof())
    cfg.add_extension(os.path.join(HERE, "ext", "plain"))
    b = await Browser.create(cfg)
    started.append(b)
    argv = cmdline(b._process_pid)
    print("1st start: load-extension in real argv:", [a for a in argv if a.startswith("--load-extension")])
    print("1st start: browser.config._browser_args:", b.config._browser_args)
    print("caller's cfg._browser_args (Browser deepcopies):", cfg._browser_args)
    await b.stop()
    # restart same instance (stop() resets _process, so start() runs again)
    try:
        await asyncio.wait_for(b.start(), 30)
        print("2nd start (same instance) succeeded? pid", b._process_pid)
        await b.stop()
    except Exception as e:
        print("2nd start (same instance) raised:", type(e).__name__, str(e).strip().splitlines()[:3])
    print("after 2nd start: browser.config._browser_args:", b.config._browser_args)
    print("after 2nd start: load-extension in config():", [a for a in b.config() if a.startswith("--load-extension")])
    print("host/port left on config:", b.config.host, b.config.port, "-> restart takes connect_existing path, no new process")
    # force a real relaunch by clearing host/port, to see whether dup reaches chromium
    b.config.host = None; b.config.port = None
    await asyncio.wait_for(b.start(), 30)
    argv = cmdline(b._process_pid)
    print("3rd start (host/port cleared): load-extension in real argv:", [a for a in argv if a.startswith("--load-extension")])
    await b.stop()

    # second Browser.create from same caller cfg: deepcopy -> no dup
    b2 = await Browser.create(cfg)
    started.append(b2)
    argv = cmdline(b2._process_pid)
    print("new Browser.create(cfg) reusing caller cfg: load-extension in argv:", [a for a in argv if a.startswith("--load-extension")])
    await b2.stop()

async def k5():
    print("\n=== K5 (real start): extension path containing 'headless' ===")
    cfg = Config(headless=True, user_data_dir=prof())
    cfg.add_extension(os.path.join(HERE, "ext", "headless-scraper", "ext"))
    try:
        b = await asyncio.wait_for(Browser.create(cfg), 30)
        started.append(b)
        print("started OK (unexpected)")
        await b.stop()
    except ValueError as e:
        print("Browser.create raised ValueError:", e)

async def main():
    try:
        await k2()
        await k3()
        await k5()
    finally:
        for b in started:
            if not b.stopped:
                await b.stop()

asyncio.run(main())
