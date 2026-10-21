import asyncio, sys, os, threading, http.server, json
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__)
seen = []
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        seen.append({k: v for k, v in self.headers.items() if k.lower().startswith("sec-ch-ua") or k.lower() == "accept-language"})
        b = b"<html><body>hi</body></html>"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=httpd.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{httpd.server_address[1]}"
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/a"); await tab.wait_for_ready_state("complete")
        print("A7.6 headers before:", seen[-1])
        await tab.set_user_agent(accept_language="de-DE")
        await tab.get(base + "/b"); await tab.wait_for_ready_state("complete")
        print("A7.6 headers after :", seen[-1])
        data, stream = await tab.send(cdp.page.print_to_pdf(transfer_mode="ReturnAsStream"))
        print("A7.12 raw: data len", len(data), "stream", stream)
        r = await tab.send(cdp.io.read(stream, size=16))
        print("A7.12 stream readable:", r[1][:8] if r[1] else r)
        await tab.send(cdp.io.close(stream))
    finally:
        await browser.stop(); httpd.shutdown()
asyncio.run(asyncio.wait_for(main(), 60))
