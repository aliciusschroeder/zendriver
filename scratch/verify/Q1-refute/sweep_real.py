"""Send many commands over a RAW websocket to real headless Chromium and run the
bundled generated parser on each raw reply, to find replies the parser rejects."""
import asyncio, json, sys, http.server, threading
import websockets
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Set-Cookie", "a=1; SameSite=Lax")
        self.send_header("Set-Cookie", "b=2; SameSite=Strict; HttpOnly")
        self.send_header("Set-Cookie", "c=3; Priority=High")
        self.end_headers()
        self.wfile.write(b"<html><body><iframe src='/frame'></iframe><p id=x>hi</p></body></html>")
    def log_message(self, *a): pass

async def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    browser = await zendriver.start(headless=True)
    try:
        ws_url = browser.connection.websocket_url
        async with websockets.connect(ws_url, max_size=2**28) as ws:
            ids = iter(range(1, 10**6))
            async def raw(method, params=None, session=None):
                i = next(ids)
                m = {"id": i, "method": method, "params": params or {}}
                if session: m["sessionId"] = session
                await ws.send(json.dumps(m))
                while True:
                    r = json.loads(await asyncio.wait_for(ws.recv(), 20))
                    if r.get("id") == i:
                        return r
            targets = (await raw("Target.getTargets"))["result"]["targetInfos"]
            page = [t for t in targets if t["type"] == "page"][0]
            sess = (await raw("Target.attachToTarget", {"targetId": page["targetId"], "flatten": True}))["result"]["sessionId"]
            await raw("Page.enable", session=sess)
            await raw("Network.enable", session=sess)
            await raw("Page.navigate", {"url": url}, session=sess)
            await asyncio.sleep(1.5)
            await raw("Network.setCookie", {"name": "p", "value": "1", "url": url.replace("http","https").replace("127.0.0.1","example.com"), "secure": True, "sameSite": "None", "partitionKey": {"topLevelSite": "https://example.com", "hasCrossSiteAncestor": False}}, session=sess)
            frame_id = (await raw("Page.getFrameTree", session=sess))["result"]["frameTree"]["frame"]["id"]
            browser_level = [
                cdp.browser.get_version(), cdp.target.get_targets(), cdp.target.get_target_info(cdp.target.TargetID(page["targetId"])),
                cdp.storage.get_cookies(), cdp.system_info.get_info(), cdp.system_info.get_process_info(),
                cdp.browser.get_window_for_target(cdp.target.TargetID(page["targetId"])), cdp.browser.get_histograms(),
                cdp.browser.get_browser_command_line(), cdp.system_info.get_feature_state("x"),
            ]
            page_level = [
                cdp.page.get_frame_tree(), cdp.page.get_resource_tree(), cdp.page.get_navigation_history(),
                cdp.page.get_layout_metrics(), cdp.page.get_app_manifest(), cdp.page.get_installability_errors(),
                cdp.page.get_app_id(), cdp.page.get_permissions_policy_state(cdp.page.FrameId(frame_id)),
                cdp.page.get_origin_trials(cdp.page.FrameId(frame_id)), cdp.network.get_cookies(), cdp.network.get_all_cookies(),
                cdp.runtime.evaluate("document.title"), cdp.runtime.evaluate("({a:[1,{b:2}]})", return_by_value=True),
                cdp.runtime.evaluate("throw new Error('x')"), cdp.runtime.evaluate("Promise.reject(1)", await_promise=True),
                cdp.runtime.evaluate("1n"), cdp.runtime.evaluate("Symbol('s')"), cdp.runtime.evaluate("NaN"),
                cdp.runtime.get_heap_usage(), cdp.runtime.get_isolate_id(), cdp.dom.get_document(depth=-1, pierce=True),
                cdp.accessibility.get_full_ax_tree(), cdp.performance.get_metrics(),
                cdp.storage.get_usage_and_quota(url.rstrip('/')), cdp.storage.get_storage_key_for_frame(cdp.page.FrameId(frame_id)),
                cdp.page.capture_screenshot(), cdp.dom_snapshot.capture_snapshot(computed_styles=[]),
                cdp.page.get_ad_script_ancestry(cdp.page.FrameId(frame_id)), cdp.css.get_media_queries() if False else cdp.runtime.evaluate("1"),
                cdp.page.get_annotated_page_content(),
            ]
            fails = 0; n = 0
            for level, cmds in (("browser", browser_level), ("page", page_level)):
                for gen in cmds:
                    d = next(gen)
                    r = await raw(d["method"], d.get("params"), sess if level == "page" else None)
                    n += 1
                    if "error" in r:
                        print(f"  {d['method']}: chrome error {r['error'].get('message')!r:.60}")
                        continue
                    try:
                        gen.send(r["result"])
                    except StopIteration:
                        continue
                    except Exception as e:
                        fails += 1
                        print(f"  PARSE FAIL {d['method']}: {type(e).__name__}: {e!r:.150}")
            print(f"commands answered: {n}, parse failures: {fails}")
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 100))
