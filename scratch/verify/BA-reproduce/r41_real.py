import asyncio, os, sys, time, subprocess, pickle, tempfile, shutil
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

def nfds():
    return len(os.listdir("/proc/self/fd"))

def x_sockets():
    n = 0
    for fd in os.listdir("/proc/self/fd"):
        try:
            if os.readlink(f"/proc/self/fd/{fd}").startswith("socket:"):
                n += 1
        except OSError:
            pass
    return n

async def main():
    xvfb = subprocess.Popen(["Xvfb", ":87", "-screen", "0", "1920x1080x24", "-nolisten", "tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.environ["DISPLAY"] = ":87"
    await asyncio.sleep(1.0)
    tmp = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
    b = await zd.start(headless=False, browser_args=["--window-size=800,600"])
    try:
        # A4.6
        try:
            await asyncio.wait_for(b.grant_all_permissions(), 20)
            print("grant_all_permissions: OK")
        except Exception as e:
            print("grant_all_permissions:", type(e).__name__, str(e).splitlines()[0])
        rejected = []
        for p in cdp.browser.PermissionType:
            try:
                await b.connection.send(cdp.browser.grant_permissions([p]))
            except Exception as e:
                rejected.append((p.value, str(e).splitlines()[0]))
        print("individually rejected:", rejected)
        # with an origin
        rejected_o = []
        for p in cdp.browser.PermissionType:
            try:
                await b.connection.send(cdp.browser.grant_permissions([p], origin="https://example.com"))
            except Exception as e:
                rejected_o.append(p.value)
        print("rejected even with origin:", rejected_o)

        # A4.7 / A4.8 real mss + real window
        await b.get("about:blank")
        s0 = x_sockets()
        for i in range(3):
            grid = await b.tile_windows()
            print("tile_windows grid:", grid)
        await asyncio.sleep(0.5)
        wid, bounds = await b.tabs[0].get_window()
        print("actual window bounds after tiling:", bounds.left, bounds.top, bounds.width, bounds.height)
        print("socket fds before/after 3 tile_windows calls:", s0, x_sockets())
        import gc; gc.collect()
        print("socket fds after gc:", x_sockets())

        # A12.6 real cookie save/load
        await b.cookies.set_all([
            cdp.network.CookieParam(name="a", value="x", domain="example.com", path="/"),
            cdp.network.CookieParam(name="b", value="y", domain="example.org", path="/"),
        ])
        f = os.path.join(tmp, "c.dat")
        await b.cookies.save(f, pattern="session")
        with open(f, "rb") as fh:
            saved = pickle.load(fh)
        print("save(pattern='session') saved:", [(c.name, c.value, c.domain) for c in saved])
        await b.cookies.save(f, pattern="secure")
        with open(f, "rb") as fh:
            print("save(pattern='secure') saved:", [c.name for c in pickle.load(fh)])
        await b.cookies.save(f, pattern="^a$")
        with open(f, "rb") as fh:
            print("save(pattern='^a$') saved:", [c.name for c in pickle.load(fh)])
        await b.cookies.save(f, pattern="example.org")
        with open(f, "rb") as fh:
            print("save(pattern='example.org') saved:", [c.name for c in pickle.load(fh)])
        await b.cookies.save(f)
        await b.cookies.clear()
        await b.cookies.load(f, pattern="path")
        print("load(pattern='path') loaded:", [c.name for c in await b.cookies.get_all()])

        # A4.1 real: close all tabs
        for t in list(b.tabs):
            await t.close()
        await asyncio.sleep(0.5)
        print("targets after closing all tabs:", [(t.type_, t.target_id[:8]) for t in b.targets])
        try:
            print("list(browser):", list(b))
        except Exception as e:
            print("list(browser):", type(e).__name__, e)
    finally:
        await b.stop()
        xvfb.terminate(); xvfb.wait()
        shutil.rmtree(tmp, ignore_errors=True)

asyncio.run(main())
