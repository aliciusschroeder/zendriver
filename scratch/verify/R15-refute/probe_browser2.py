import asyncio, collections, os, sys, signal
import zendriver
import zendriver.core.util as zutil
from zendriver import Config, cdp

D = os.path.dirname(os.path.abspath(__file__))
HEADLESS = os.environ.get("HEADFUL") != "1"
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0], "headless", HEADLESS)
captured = []
_orig = zutil._start_process
started = []
def spy(exe, params, is_posix, env=None):
    captured.append(list(params))
    p = _orig(exe, params, is_posix, env=env)
    started.append(p)
    return p
zutil._start_process = spy

def dups(lst):
    return {k: v for k, v in collections.Counter(lst).items() if v > 1}

def count(prefix, params):
    return sum(a.startswith(prefix) for a in params)

async def ext_targets(browser, tries=20):
    for _ in range(tries):
        ts = await browser.connection.send(cdp.target.get_targets())
        e = sorted({t.url for t in ts if t.url.startswith("chrome-extension://")})
        if e:
            return e
        await asyncio.sleep(0.25)
    return []

async def ev(b, expr):
    return await b.main_tab.evaluate(expr)

async def main():
    if not HEADLESS:
        b = await zendriver.start(headless=False, lang="de-DE", browser_args=["--lang=fr-FR"])
        try:
            print("HEADFUL user --lang=fr-FR + Config lang=de-DE: order", [a for a in captured[-1] if a.startswith("--lang")],
                  "-> navigator.language =", await ev(b, "navigator.language"))
        finally:
            await b.stop()
        b = await zendriver.start(headless=False, browser_args=["--lang=fr-FR"])
        try:
            print("HEADFUL only --lang=fr-FR -> navigator.language =", await ev(b, "navigator.language"))
        finally:
            await b.stop()
        return

    # Chrome: last value wins for duplicated value switches?
    b = await zendriver.start(headless=True, browser_args=["--window-size=800,600", "--window-size=1000,700",
                                                          "--user-agent=AAA", "--user-agent=BBB"])
    try:
        print("CHROME dup value switches: window outer =", await ev(b, "[window.outerWidth, window.outerHeight]"))
        ver = await b.connection.send(cdp.browser.get_version())
        print("CHROME dup --user-agent: Browser.getVersion UA =", ver[3])
    finally:
        await b.stop()

    # Chrome: identical --load-extension twice
    p = os.path.join(D, "ext", "plain-ext")
    b = await zendriver.start(headless=True, browser_args=[f"--load-extension={p}", f"--load-extension={p}",
                                                          "--enable-unsafe-extension-debugging"])
    try:
        print("CHROME identical --load-extension x%d -> ext targets:" % count("--load-extension", captured[-1]), await ext_targets(b))
    finally:
        await b.stop()

    # K3 path 1: same Browser, start() again after stop()
    cfg = Config(headless=True)
    cfg.add_extension(p)
    before = list(cfg._browser_args)
    b = await zendriver.Browser.create(cfg)
    print("K3 #1: launches so far", len(started), "--load-extension in argv:", count("--load-extension", captured[-1]),
          "ext:", await ext_targets(b))
    print("K3 #1: config host/port after start:", b.config.host, b.config.port)
    await b.stop()
    n = len(started)
    try:
        await asyncio.wait_for(b.start(), 30)
        print("K3 restart-after-stop: returned normally")
    except Exception as e:
        print("K3 restart-after-stop: raised", type(e).__name__, str(e)[:80].strip())
    print("K3 restart-after-stop: new chrome launched?", len(started) != n,
          "| --load-extension entries in b.config._browser_args:", count("--load-extension", b.config._browser_args))
    try:
        await b.stop()
    except Exception as e:
        print("stop raised", e)

    # K3 path 2: chrome died, start() -> create(config=self.config)
    b = await zendriver.Browser.create(cfg)
    proc = b._process
    proc.kill(); proc.wait()
    n = len(started)
    try:
        nb = await asyncio.wait_for(b.start(), 30)
        print("K3 process-died restart: returned", nb is b, "launched?", len(started) != n)
        if nb is not b:
            print("   new argv --load-extension count:", count("--load-extension", captured[-1]) if len(started) != n else None)
            await nb.stop()
    except Exception as e:
        print("K3 process-died restart: raised", type(e).__name__, "| new chrome launched?", len(started) != n)
    b._process = None; b._process_pid = None
    await b.stop()
    print("K3: caller Config._browser_args mutated?", cfg._browser_args != before)

    # K3: same Config reused for a fresh Browser
    b2 = await zendriver.Browser.create(cfg)
    print("K3 second Browser from same Config: --load-extension in argv:", count("--load-extension", captured[-1]))
    await b2.stop()

    # K4 via public entry points
    mine = ["--mute-audio"]
    cfg = Config(headless=True, browser_args=mine)
    cfg.add_extension(p)
    b = await zendriver.Browser.create(cfg)
    await b.stop()
    print("K4: caller list after Browser.create(cfg with extension):", mine)
    mine2 = ["--mute-audio"]
    b = await zendriver.start(headless=True, browser_args=mine2)
    await b.stop()
    print("K4: caller list after zendriver.start(browser_args=mine):", mine2)

    # K4 shared list across two Configs with add_argument
    BASE = ["--mute-audio"]
    c1 = Config(headless=True, browser_args=BASE); c1.add_argument("--window-size=800,600")
    c2 = Config(headless=True, browser_args=BASE); c2.add_argument("--window-size=1000,700")
    b = await zendriver.Browser.create(c1)
    try:
        print("K4 shared list: c1 argv window-size:", [a for a in captured[-1] if a.startswith("--window-size")],
              "-> c1's window:", await ev(b, "[window.outerWidth, window.outerHeight]"))
    finally:
        await b.stop()

    # K5 end-to-end
    for sub in ["languagetool", "headless-bot/ublock"]:
        c = Config(headless=True)
        c.add_extension(os.path.join(D, "ext", sub))
        n = len(started)
        try:
            b = await zendriver.Browser.create(c)
        except ValueError as e:
            print(f"K5: extension at .../ext/{sub} -> ValueError: {e}"[:200], "| chrome launched?", len(started) != n)
        else:
            print(f"K5: extension at .../ext/{sub} worked")
            await b.stop()
    q = os.path.join(D, "ext", "languagetool")
    b = await zendriver.start(headless=True, browser_args=[f"--load-extension={q}", "--enable-unsafe-extension-debugging"])
    try:
        print("K5-control: same extension via constructor browser_args -> ext:", await ext_targets(b))
    finally:
        await b.stop()

async def runner():
    try:
        await asyncio.wait_for(main(), 110)
    finally:
        alive = [p.pid for p in started if p.poll() is None]
        print("my chrome pids:", [p.pid for p in started], "still alive:", alive)
        for p in started:
            if p.poll() is None:
                p.kill()

asyncio.run(runner())
