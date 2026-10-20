import asyncio, threading, http.server, socketserver, os, pathlib
import zendriver as zd

HERE = pathlib.Path(__file__).parent
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/file"):
            body = b"hello"
            self.send_response(200); self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f"attachment; filename={self.path[1:].replace('?','_').replace('=','_')}.bin")
        else:
            body = b"<html><body><a id=l href='/file?n=exp'>dl</a></body></html>"
            self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"

async def main():
    dl = HERE / "dl_target"; dl.mkdir(exist_ok=True)
    for f in dl.iterdir(): f.unlink()
    b = await zd.start(headless=True)
    tab1 = await b.get(base + "/page")
    await tab1.set_download_path(dl)
    await tab1.download_file(base + "/file?n=before", "before.bin")
    await asyncio.sleep(1.5)
    print("tab1 download before expectation lands in dl dir:", sorted(p.name for p in dl.iterdir()))
    tab2 = await b.get(base + "/page", new_tab=True)
    async with tab2.expect_download() as exp:
        await (await tab2.select("#l")).click()
        ev = await asyncio.wait_for(exp.value, 10)
    print("tab1._download_behavior still says:", tab1._download_behavior)
    await tab1.download_file(base + "/file?n=after", "after.bin")
    await asyncio.sleep(1.5)
    print("files in dl dir after tab2 expectation + tab1 download:", sorted(p.name for p in dl.iterdir()))
    await b.stop()

asyncio.run(asyncio.wait_for(main(), 50))
