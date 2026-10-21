import asyncio
import http.server
import sys
import threading
import warnings

import zendriver as zd
from zendriver import cdp

warnings.simplefilter("ignore")
print("zendriver from", zd.__file__)


async def q(tab, name):
    return await tab.evaluate(
        f"navigator.permissions.query({{name:'{name}'}}).then(p => p.state, e => 'ERR ' + e)",
        await_promise=True,
    )


async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zd.start(headless=True)
    try:
        tab = browser.tabs[0]
        await tab.get(url)
        print("before:", {n: await q(tab, n) for n in ("geolocation", "notifications", "midi")})
        try:
            await browser.grant_all_permissions()
            print("grant_all_permissions: OK")
        except Exception as e:
            print("grant_all_permissions:", type(e).__name__, str(e).splitlines()[0])
        print("after all:", {n: await q(tab, n) for n in ("geolocation", "notifications", "midi")})
        rejected, ok = [], []
        for p in cdp.browser.PermissionType:
            try:
                await browser.connection.send(cdp.browser.grant_permissions([p]))
                ok.append(p.value)
            except Exception as e:
                rejected.append((p.value, str(e).splitlines()[0]))
        print("ok:", len(ok), "rejected:", rejected)
        print("after single:", {n: await q(tab, n) for n in ("geolocation", "notifications", "midi")})
        await browser.connection.send(cdp.browser.grant_permissions([cdp.browser.PermissionType.GEOLOCATION], origin=url.rstrip("/")))
        print("after origin grant:", await q(tab, "geolocation"))
        await tab.reload()
        print("after reload:", await q(tab, "geolocation"))
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
