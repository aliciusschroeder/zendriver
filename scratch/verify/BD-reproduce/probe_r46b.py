import asyncio, os, sys, threading, http.server, socketserver
import zendriver as zd
from zendriver import cdp
from zendriver.cdp.fetch import RequestStage
from zendriver.cdp.network import ResourceType
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

PAGE = b"""<!doctype html><html><body><script>
window.__a=null; window.__b=null;
fetch('/a.json').then(r=>r.text()).then(t=>window.__a=t);
setTimeout(()=>fetch('/b.json').then(r=>r.text()).then(t=>window.__b=t), 300);
</script></body></html>"""
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/page"):
            body, ct = PAGE, "text/html"
        elif self.path.startswith("/a.json"):
            body, ct = b'{"a":1}', "application/json"
        elif self.path.startswith("/b.json"):
            body, ct = b'{"b":2}', "application/json"
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"

async def try_(label, coro, t=5):
    try:
        r = await asyncio.wait_for(coro, t); print(f"   {label}: {r!r}"[:300]); return r
    except asyncio.TimeoutError:
        print(f"   {label}: TIMEOUT ({t}s)")
    except Exception as e:
        print(f"   {label}: {type(e).__name__}: {str(e).splitlines()[0][:150]}")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get(BASE + "/blank")
        print("[A10.2 scenario 1: nested, both active]")
        async with tab.intercept("*a.json*", RequestStage.REQUEST, ResourceType.XHR) as a:
            async with tab.intercept("*b.json*", RequestStage.REQUEST, ResourceType.XHR) as b:
                await try_("tab.get(page)", tab.get(BASE + "/page"), 10)
                ra = await try_("a.request.url", _url(a), 5)
                rb = await try_("b.request.url", _url(b), 5)
                await try_("a.continue_request()", _cont(a), 5)
                await try_("b.continue_request()", _cont(b), 5)
                await asyncio.sleep(1)
                await try_("window.__a/__b", tab.evaluate("[window.__a, window.__b]"), 5)
        print("[A10.2 scenario 2: inner exits before outer matched]")
        await tab.get(BASE + "/blank")
        async with tab.intercept("*a.json*", RequestStage.REQUEST, ResourceType.XHR) as a:
            async with tab.intercept("*b.json*", RequestStage.REQUEST, ResourceType.XHR) as b:
                pass
            print("   fetch in manually_enabled_domains:", cdp.fetch in tab.manually_enabled_domains,
                  "| RequestPaused handlers:", len(tab.handlers.get(cdp.fetch.RequestPaused, [])))
            gt = asyncio.ensure_future(tab.get(BASE + "/page2"))
            done, pending = await asyncio.wait([gt], timeout=8)
            if pending:
                print("   tab.get(page2) still pending after 8s; stack:")
                gt.print_stack(file=sys.stdout)
                gt.cancel()
                try: await gt
                except BaseException: pass
            else:
                print("   tab.get(page2) returned", gt.exception() or "ok")
            await try_("outer a.request.url", _url(a), 3)
            await try_("window.__a/__b (inside outer)", tab.evaluate("[window.__a, window.__b, location.href]"), 5)
        print("   fetch in manually_enabled_domains after outer exit:", cdp.fetch in tab.manually_enabled_domains, "enabled_domains:", cdp.fetch in tab.enabled_domains)
    finally:
        await browser.stop(); srv.shutdown(); print("browser stopped")

async def _cont(i):
    if not i.response_future.done():
        return 'future not resolved'
    return await i.continue_request()

async def _url(i):
    return (await asyncio.shield(i.response_future)).request.url

asyncio.run(asyncio.wait_for(main(), 110))
