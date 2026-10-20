import asyncio, threading, http.server, socketserver
import zendriver as zd
from zendriver import cdp

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        body = (b"<html><body>p</body></html>" if not self.path.startswith("/data") else ("ok" + self.path).encode())
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
errors = []
async def main():
    asyncio.get_running_loop().set_exception_handler(lambda l, c: errors.append(repr(c.get("exception"))))
    b = await zd.start(headless=True)
    tab = await b.get(base + "/page")
    async with tab.intercept("*data*", cdp.fetch.RequestStage.RESPONSE, cdp.network.ResourceType.XHR) as icp:
        tab.add_handler(cdp.fetch.RequestPaused, lambda ev: print("PAUSED", ev.request.url[-8:], ev.resource_type));print("entering"); await asyncio.wait_for(tab.evaluate("window.res = []; for (let i=0;i<5;i++) fetch('/data?n='+i).then(r=>r.text()).then(t=>window.res.push(t), e=>window.res.push('ERR '+e)); 1"), 5); print("evaluated")
        req = await asyncio.wait_for(icp.request, 10)
        print("intercepted", req.url[-8:])
        await icp.continue_request()
        await asyncio.sleep(1.0)
        print("inside block, completed fetches:", await tab.evaluate("window.res.length"))
    await asyncio.sleep(1.5)
    print("after block, completed fetches:", await tab.evaluate("JSON.stringify(window.res)"), "| loop errors:", errors[:2], len(errors))
    await b.stop()
asyncio.run(asyncio.wait_for(main(), 50))
