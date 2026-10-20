import asyncio, threading, functools, http.server, socketserver
import zendriver as zd
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Q, directory="www"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
async def main():
    b = await zd.start(headless=True)
    try:
        tab = b.main_tab
        await tab.get(BASE + "/later.html")
        print("enabled domains before expect:", [m.__name__ for m in tab.enabled_domains])
        async with tab.expect_request(r".*a\.png\?later=1") as r:
            try:
                ev = await asyncio.wait_for(r.value, 5)
                print("got request", ev.request.url)
            except TimeoutError:
                print("expect_request never resolved within 5s; enabled domains:", [m.__name__ for m in tab.enabled_domains])
        # control: same, but with one unrelated send after entering
        await tab.get(BASE + "/later.html")
        async with tab.expect_request(r".*a\.png\?later=1") as r:
            await tab.evaluate("1")
            ev = await asyncio.wait_for(r.value, 5)
            print("control (with a send after enter): got", ev.request.url.rsplit('/',1)[-1])
    finally:
        await b.stop(); srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 60))
