import asyncio, logging, sys, collections, http.server, threading, functools
import zendriver as zd
from zendriver import cdp
fails = collections.Counter()
samples = {}
class H(logging.Handler):
    def emit(self, r):
        m = r.getMessage()
        if "during parsing of json from event" in m:
            key = m.split(" during")[0] + " | " + m.split("'method': '")[1].split("'")[0]
            fails[key]+=1; samples.setdefault(key, m[:600])
logging.getLogger("zendriver").addHandler(H()); logging.getLogger("zendriver").setLevel(logging.INFO)
srv = http.server.ThreadingHTTPServer(("127.0.0.1",0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=sys.argv[1]))
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
async def main():
    b = await zd.start(headless=True)
    tab = b.main_tab
    for mod in (cdp.network, cdp.page, cdp.runtime, cdp.log, cdp.audits, cdp.dom, cdp.css, cdp.security, cdp.inspector, cdp.performance, cdp.preload):
        tab.add_handler(mod, lambda e: None)
    tab = await asyncio.wait_for(b.get(url), 30)
    await tab.sleep(3)
    cmds = {
      "storage.get_cookies": cdp.storage.get_cookies(),
      "network.get_cookies": cdp.network.get_cookies(),
      "page.get_frame_tree": cdp.page.get_frame_tree(),
      "page.get_resource_tree": cdp.page.get_resource_tree(),
      "page.get_navigation_history": cdp.page.get_navigation_history(),
      "page.get_layout_metrics": cdp.page.get_layout_metrics(),
      "page.get_app_manifest": cdp.page.get_app_manifest(),
      "dom.get_document": cdp.dom.get_document(depth=-1, pierce=True),
      "target.get_targets": cdp.target.get_targets(),
      "accessibility.get_full_ax_tree": cdp.accessibility.get_full_ax_tree(),
      "dom_snapshot.capture_snapshot": cdp.dom_snapshot.capture_snapshot(computed_styles=[]),
      "runtime.evaluate": cdp.runtime.evaluate("({a:1})"),
      "browser.get_version": cdp.browser.get_version(),
      "system_info.get_info": cdp.system_info.get_info(),
      "page.get_permissions_policy_state": cdp.page.get_permissions_policy_state(tab.target.target_id),
      "page.get_origin_trials": cdp.page.get_origin_trials(tab.target.target_id),
    }
    for name, c in cmds.items():
        try:
            r = await asyncio.wait_for(tab.send(c), 10)
            print("OK  ", name)
        except asyncio.TimeoutError:
            print("HANG", name); 
        except Exception as e:
            print("ERR ", name, type(e).__name__, str(e)[:300])
    print("listener running:", tab.listener and tab.listener.running, tab.listener.task.done() if tab.listener and tab.listener.task else None)
    if tab.listener and tab.listener.task and tab.listener.task.done():
        print("listener exc:", repr(tab.listener.task.exception())[:400])
    for k,v in fails.items(): print("EVENTFAIL", v, k); print("   ", samples[k][:400])
    await b.stop()
asyncio.run(asyncio.wait_for(main(), 150))
