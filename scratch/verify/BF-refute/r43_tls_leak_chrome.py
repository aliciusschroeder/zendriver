import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zendriver as zd
from zendriver import cdp
import fakeinfra as F
print("zendriver from", zd.__file__, sys.version.split()[0])

async def run(browser, up_tls, close_mode):
    F.EV.clear()
    os_, oport = await F.start_origin(tls=True)
    ps, pport = await F.start_connect_proxy(oport, tls=up_tls)
    scheme = "https" if up_tls else "http"
    tab = await browser.create_context("about:blank", proxy_server=f"{scheme}://u:p@127.0.0.1:{pport}",
                                       proxy_ssl_context=F.insecure_client_ctx())
    fw = browser._proxy_forwarders[-1]
    await tab.get("https://origin.test/")
    await asyncio.sleep(1)
    html = await tab.get_content()
    print(f"[{scheme} upstream, {close_mode}] page ok:", "hello" in html, "| tasks before close:", len(fw._client_tasks))
    if close_mode == "dispose":
        ctx = tab.target.browser_context_id
        await tab.close()
        await browser.connection.send(cdp.target.dispose_browser_context(ctx))
    else:
        await tab.close()
    for t in (1, 3, 8):
        await asyncio.sleep(t - (0 if t == 1 else prevt[0])); prevt[0] = t
        print(f"   {t}s after {close_mode}: forwarder tasks alive = {len(fw._client_tasks)}")
    print("   events:", F.EV)
    ps.close(); os_.close()
prevt = [0]
async def main():
    browser = await zd.start(headless=True, browser_args=["--ignore-certificate-errors"])
    try:
        for up_tls in (False, True):
            prevt[0] = 0
            await run(browser, up_tls, "dispose")
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 100))
