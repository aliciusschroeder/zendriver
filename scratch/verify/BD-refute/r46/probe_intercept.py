import asyncio, sys, pathlib, threading, functools, http.server, time
import zendriver as zd
from zendriver import cdp
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(HERE / "www")))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
FETCH_BOTH = "window.__a=null; window.__b=null; fetch('/a.json').then(r=>r.text()).then(t=>window.__a=t); fetch('/b.json').then(r=>r.text()).then(t=>window.__b=t); 1"

async def w(label, aw, t=8):
    try:
        r = await asyncio.wait_for(aw, t); print(f"[{label}] OK -> {r!r}"[:200]); return r
    except asyncio.TimeoutError:
        print(f"[{label}] TIMEOUT {t}s")
    except Exception as e:
        print(f"[{label}] EXC {type(e).__name__}: {str(e)[:150]}")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(BASE + "/page.html")
        await tab.sleep(0.5)
        # control: single intercept on a.json works
        async with tab.intercept("*a.json*", RequestStage.REQUEST, ResourceType.XHR) as a:
            await tab.evaluate(FETCH_BOTH)
            ra = await w("control a.request.url", a.request)
            await a.continue_request()
        await asyncio.sleep(1)
        print("control __a/__b:", await tab.evaluate("[window.__a, window.__b]"))
        # scenario 1: nested
        print("--- scenario 1 nested")
        async with tab.intercept("*a.json*", RequestStage.REQUEST, ResourceType.XHR) as a:
            async with tab.intercept("*b.json*", RequestStage.REQUEST, ResourceType.XHR) as b:
                await tab.evaluate(FETCH_BOTH)
                ra = await w("outer a.request", a.request)
                rb = await w("inner b.request", b.request)
                if ra: print("   a got url:", ra.url)
                if rb: print("   b got url:", rb.url)
                await w("a.continue_request", a.continue_request())
                await w("b.continue_request", b.continue_request())
        await asyncio.sleep(1)
        print("scenario1 __a/__b:", await tab.evaluate("[window.__a, window.__b]"))
        # scenario 2: inner exits before outer matched
        print("--- scenario 2 inner exits first")
        tab = await browser.get(BASE + "/page.html"); await tab.sleep(0.5)
        async with tab.intercept("*a.json*", RequestStage.REQUEST, ResourceType.XHR) as a:
            async with tab.intercept("*b.json*", RequestStage.REQUEST, ResourceType.XHR) as b:
                pass
            print("   fetch in manually_enabled:", cdp.fetch in tab.manually_enabled_domains, "| handlers:", len(tab.handlers.get(cdp.fetch.RequestPaused, [])))
            await w("evaluate fetch both", tab.evaluate(FETCH_BOTH))
            print("   fetch in enabled_domains after next send:", cdp.fetch in tab.enabled_domains)
            await asyncio.sleep(2)
            print("   a done?", a.response_future.done(), (a.response_future.result().request.url if a.response_future.done() else ""))
            print("   __a/__b inside outer:", await w("eval", tab.evaluate("[window.__a, window.__b]")))
            # navigation inside outer block
            await w("tab.evaluate location.href=page2", tab.evaluate(f"location.href='{BASE}/page2.html'; 1"))
            await asyncio.sleep(4)
            print("   document title after 4s:", await w("title", tab.evaluate("document.title + '|' + location.href")))
        await asyncio.sleep(1)
        print("   after outer exit title:", await w("title", tab.evaluate("document.title + '|' + location.href")))
        print("   enabled fetch?", cdp.fetch in tab.enabled_domains, cdp.fetch in tab.manually_enabled_domains)
    finally:
        await browser.stop()
        srv.shutdown()
asyncio.run(main())
