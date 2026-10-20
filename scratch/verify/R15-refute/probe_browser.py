import asyncio, collections, os, sys
import zendriver
import zendriver.core.util as zutil
from zendriver import Config, cdp

D = os.path.dirname(os.path.abspath(__file__))
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
captured = []
_orig = zutil._start_process
started_pids = []
def spy(exe, params, is_posix, env=None):
    captured.append(list(params))
    p = _orig(exe, params, is_posix, env=env)
    started_pids.append(p.pid)
    return p
zutil._start_process = spy

def dups(lst):
    return {k: v for k, v in collections.Counter(lst).items() if v > 1}

async def ext_targets(browser):
    ts = await browser.connection.send(cdp.target.get_targets())
    return sorted({t.url for t in ts if t.url.startswith("chrome-extension://")})

async def nav_eval(browser, expr):
    tab = browser.main_tab
    return await tab.evaluate(expr)

async def wait_ext(browser, tries=20):
    for _ in range(tries):
        e = await ext_targets(browser)
        if e:
            return e
        await asyncio.sleep(0.25)
    return []

async def main():
    # A1/A2/A3: duplicates of Config-owned flags; which value wins
    b = await zendriver.start(headless=True, lang="de-DE", user_agent="UA-from-config",
                              browser_args=["--headless=new", "--no-sandbox", "--lang=fr-FR",
                                            "--user-agent=UA-from-user-args"])
    try:
        print("A: launched OK with dups:", dups(captured[-1]))
        print("A: navigator.language =", await nav_eval(b, "navigator.language"),
              "| languages =", await nav_eval(b, "navigator.languages"))
        print("A: navigator.userAgent =", await nav_eval(b, "navigator.userAgent"))
        ver = await b.connection.send(cdp.browser.get_version())
        print("A: Browser.getVersion userAgent =", ver[3] if isinstance(ver, tuple) else ver)
    finally:
        await b.stop()

    # control: only user --lang=fr-FR (no Config lang): does headless honour --lang at all?
    b = await zendriver.start(headless=True, browser_args=["--lang=fr-FR"])
    try:
        print("A-control: navigator.language with only --lang=fr-FR =", await nav_eval(b, "navigator.language"))
    finally:
        await b.stop()

    # K3: same Browser started again after stop, with an extension
    cfg = Config(headless=True)
    cfg.add_extension(os.path.join(D, "ext", "plain-ext"))
    user_args_before = list(cfg._browser_args)
    b = await zendriver.Browser.create(cfg)
    try:
        print("K3 start#1 --load-extension count:", sum(a.startswith("--load-extension") for a in captured[-1]))
        print("K3 start#1 ext targets:", await wait_ext(b))
    finally:
        await b.stop()
    await b.start()
    try:
        print("K3 start#2 (same Browser after stop) --load-extension count:",
              sum(a.startswith("--load-extension") for a in captured[-1]), "dups:", dups(captured[-1]))
        print("K3 start#2 ext targets:", await wait_ext(b))
    finally:
        await b.stop()
    await b.start()
    try:
        print("K3 start#3 --load-extension count:", sum(a.startswith("--load-extension") for a in captured[-1]))
        print("K3 start#3 ext targets:", await wait_ext(b))
    finally:
        await b.stop()
    print("K3: caller Config._browser_args mutated by starts?", cfg._browser_args != user_args_before, cfg._browser_args)
    # same Config reused for a second Browser
    b2 = await zendriver.Browser.create(cfg)
    try:
        print("K3 second Browser from same Config --load-extension count:",
              sum(a.startswith("--load-extension") for a in captured[-1]))
    finally:
        await b2.stop()

    # K4 via public entry point with an extension: caller list mutated?
    mine = ["--mute-audio"]
    cfg = Config(headless=True, browser_args=mine)
    cfg.add_extension(os.path.join(D, "ext", "plain-ext"))
    b = await zendriver.Browser.create(cfg)
    await b.stop()
    print("K4: caller list after Browser.create+start with extension:", mine)
    mine2 = ["--mute-audio"]
    b = await zendriver.start(headless=True, browser_args=mine2)
    await b.stop()
    print("K4: caller list after zendriver.start:", mine2)

    # K5 end to end: extension folder whose path contains 'lang' / 'headless'
    for sub in ["languagetool", "headless-bot/ublock"]:
        cfg = Config(headless=True)
        cfg.add_extension(os.path.join(D, "ext", sub))
        n_before = len(captured)
        try:
            b = await zendriver.Browser.create(cfg)
        except ValueError as e:
            print(f"K5: Browser.create with extension at .../{sub} -> ValueError: {e}")
            print("K5: chrome launched?", len(captured) != n_before)
        else:
            print(f"K5: Browser.create with extension at .../{sub} worked")
            await b.stop()

    # K5 control: same extension passed through constructor browser_args (no validation)
    path = os.path.join(D, "ext", "languagetool")
    b = await zendriver.start(headless=True, browser_args=[f"--load-extension={path}", "--enable-unsafe-extension-debugging"])
    try:
        print("K5-control: languagetool via browser_args ext targets:", await wait_ext(b))
    finally:
        await b.stop()

async def runner():
    try:
        await asyncio.wait_for(main(), 100)
    finally:
        print("pids started:", started_pids)

asyncio.run(runner())
