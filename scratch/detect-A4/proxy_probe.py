import asyncio, os, socket, threading, time
import zendriver as zd

# a fake "corporate proxy" that records and refuses requests
hits = []
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(16)
port = srv.getsockname()[1]
def serve():
    while True:
        c, _ = srv.accept()
        data = c.recv(4096)
        hits.append(data.split(b"\r\n")[0])
        c.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        c.close()
threading.Thread(target=serve, daemon=True).start()

for k in list(os.environ):
    if k.lower() in ("no_proxy", "http_proxy", "https_proxy", "all_proxy"):
        del os.environ[k]
os.environ["http_proxy"] = f"http://127.0.0.1:{port}"

async def main():
    t = time.time()
    try:
        b = await zd.start(headless=True, browser_connection_max_tries=3)
        print("started OK", b.info)
        await b.stop()
    except Exception as e:
        print("start failed after %.1fs:" % (time.time() - t), type(e).__name__, str(e).strip().splitlines()[:3])
    print("requests seen by proxy:", hits[:5])
asyncio.run(main())
