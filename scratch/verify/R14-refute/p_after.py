"""What still works in b1 after b2's failed start deleted its profile? Also gather() variant."""
import asyncio
import functools
import http.server
import os
import sys
import tempfile
import threading

import zendriver as zd
from zendriver import cdp

print("python:", sys.version.split()[0], "| zendriver from:", zd.__file__)
VARIANT = sys.argv[1]  # seq | gather
started = []


def serve():
    d = tempfile.mkdtemp(prefix="www_")
    with open(os.path.join(d, "index.html"), "w") as f:
        f.write("<title>idx</title>hi")
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=d)
    h.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, d


async def main():
    srv, wwwdir = serve()
    url = "http://127.0.0.1:%d/index.html" % srv.server_address[1]
    config = zd.Config(headless=True)
    print(config.__class__.__name__, "repr len", len(repr(config)))
    if VARIANT == "gather":
        res = await asyncio.wait_for(asyncio.gather(zd.start(config), zd.start(config), return_exceptions=True), 90)
        ok = [r for r in res if isinstance(r, zd.Browser)]
        bad = [r for r in res if not isinstance(r, zd.Browser)]
        started.extend(ok)
        print("gather: started", len(ok), "failed", [type(b).__name__ + (": Failed to connect" if "Failed to connect" in str(b) else str(b)[:100]) for b in bad])
        b1 = ok[0]
    else:
        b1 = await asyncio.wait_for(zd.start(config), 60)
        started.append(b1)
        try:
            b2 = await asyncio.wait_for(zd.start(config), 60)
            started.append(b2)
            print("b2 started?!")
        except Exception as e:
            print("b2 failed:", "Failed to connect" in str(e))
    print("b1 alive:", b1._process.poll() is None, "| b1 profile exists:", os.path.isdir(b1.config.user_data_dir))

    tab = await asyncio.wait_for(b1.get(url), 30)
    await tab.wait_for_ready_state("complete")
    print("nav ok, title:", await tab.evaluate("document.title"))
    print("localStorage:", await tab.evaluate("localStorage.setItem('k','v'); localStorage.getItem('k')"))
    await tab.evaluate("document.cookie='c=1; max-age=3600'")
    await tab.reload()
    await tab.wait_for_ready_state("complete")
    print("cookie after reload:", await tab.evaluate("document.cookie"))
    cookies = await b1.connection.send(cdp.storage.get_cookies())
    print("cdp cookies:", [(c.name, c.value) for c in cookies])
    t2 = await asyncio.wait_for(b1.get(url, new_tab=True), 30)
    await t2.wait_for_ready_state("complete")
    print("new tab ok, localStorage shared:", await t2.evaluate("localStorage.getItem('k')"))
    try:
        ctx_tab = await asyncio.wait_for(b1.create_context(url), 30)
        print("new context tab ok")
    except Exception as e:
        print("create_context error:", type(e).__name__, str(e)[:200])
    print("b1 profile exists at end:", os.path.isdir(b1.config.user_data_dir))
    for b in list(started):
        await b.stop()
    srv.shutdown()
    import shutil
    shutil.rmtree(wwwdir)


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
