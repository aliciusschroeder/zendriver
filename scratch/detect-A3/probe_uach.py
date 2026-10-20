import asyncio, json, subprocess, tempfile, shutil, urllib.request, threading, http.server, sys
import websockets

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b=b"<html>hi</html>"; self.send_response(200); self.send_header("Content-Type","text/html"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1",0),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
URL=f"http://127.0.0.1:{srv.server_address[1]}/"

async def call(ws, i, method, params):
    await ws.send(json.dumps({"id":i,"method":method,"params":params}))
    while True:
        m = json.loads(await ws.recv())
        if m.get("id")==i: return m

async def main():
    udd = tempfile.mkdtemp(prefix="a3probe_")
    port = 9556
    p = subprocess.Popen(["chromium", "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}", f"--user-data-dir={udd}", "--remote-allow-origins=*", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                pages = [t for t in targets if t["type"] == "page"]
                if pages: break
            except Exception: pass
            await asyncio.sleep(0.2)
        async with websockets.connect(pages[0]["webSocketDebuggerUrl"]) as ws:
            await call(ws,1,"Page.navigate",{"url":URL})
            await asyncio.sleep(1)
            m = await call(ws,2,"Runtime.evaluate",{"expression":"navigator.userAgentData.getHighEntropyValues(['architecture','bitness','platformVersion','model','platform','formFactors']).then(JSON.stringify)","awaitPromise":True,"returnByValue":True})
            print("chrome's own hints:", m["result"]["result"].get("value"))
    finally:
        p.kill(); p.wait(); shutil.rmtree(udd, ignore_errors=True)

asyncio.run(main())
