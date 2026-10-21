import asyncio, sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
logs = []
class H(logging.Handler):
    def emit(self, r):
        if r.levelno >= logging.WARNING and r.name in ("asyncio", "zendriver.core.proxy"):
            logs.append((r.name, r.getMessage().splitlines()[0][:90], r.exc_info[0].__name__ if r.exc_info else None))
logging.getLogger().addHandler(H())
seen = []
async def socks_server():
    async def h(r, w):
        try:
            await r.readexactly(4); w.write(b"\x05\x02")
            v, ul = await r.readexactly(2); await r.readexactly(ul); (pl,) = await r.readexactly(1); await r.readexactly(pl)
            w.write(b"\x01\x00")
            hdr = await r.readexactly(4); atyp = hdr[3]
            if atyp == 3:
                (l,) = await r.readexactly(1); name = await r.readexactly(l); await r.readexactly(2); seen.append(name)
            # reply host unreachable
            w.write(b"\x05\x04\x00\x01" + bytes(6))
        except Exception: pass
        finally: w.close()
    s = await asyncio.start_server(h, "127.0.0.1", 0)
    return s, s.sockets[0].getsockname()[1]
async def main():
    ss, sport = await socks_server()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.create_context("about:blank", proxy_server=f"socks5://u:p@127.0.0.1:{sport}")
        for url in ["https://ok.example.com/", "https://" + "a"*64 + ".example.com/", "http://a..b.com/", "https://a..b.com/", "http://" + "b"*64 + ".example.com/"]:
            logs.clear()
            await tab.send(cdp.page.navigate(url))
            await asyncio.sleep(2)
            ev = await tab.evaluate("location.href")
            title = await tab.evaluate("document.body ? document.body.innerText.slice(0,80) : ''")
            print(f"{url[:40]:42s} logs={logs} | page={title!r}")
        print("socks server saw domains:", seen)
    finally:
        await browser.stop(); ss.close()
asyncio.run(asyncio.wait_for(main(), 100))
