import asyncio, sys, os, time
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
MODES = {
 "value": "inp.value='tok';",
 "remove": "inp.remove();",
 "navigate": "location.href='/solved';",
 "value_then_nav_300ms": "inp.value='tok'; setTimeout(()=>{location.href='/solved'},300);",
 "value_then_nav_3s": "inp.value='tok'; setTimeout(()=>{location.href='/solved'},3000);",
 "reload": "inp.value='tok'; location.reload();",
}
def page(mode):
    return f"""<!doctype html><html><body>
<div id=host style="width:320px;height:70px"></div>
<input type=hidden name=cf-turnstile-response value="">
<script>
const inp=document.querySelector('input[name=cf-turnstile-response]');
const h=document.getElementById('host'); const sr=h.attachShadow({{mode:'closed'}});
const d=document.createElement('div'); d.setAttribute('data-src','https://challenges.cloudflare.com/x');
d.style.cssText='width:300px;height:65px;background:#ccc'; sr.appendChild(d);
d.addEventListener('click',()=>{{ {MODES[mode]} }});
</script></body></html>"""

async def serve():
    async def h(r, w):
        head = await r.readuntil(b"\r\n\r\n")
        path = head.split(b" ")[1].decode()
        if path.startswith("/m/"):
            body = page(path[3:]).encode()
        else:
            body = b"<html><body>solved</body></html>"
        w.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(body) + body)
        await w.drain(); w.close()
    s = await asyncio.start_server(h, "127.0.0.1", 0)
    return s, s.sockets[0].getsockname()[1]

async def main():
    s, port = await serve()
    browser = await zd.start(headless=True)
    try:
        for mode in MODES:
            tab = await browser.get(f"http://127.0.0.1:{port}/m/{mode}")
            await asyncio.sleep(0.5)
            t0 = time.monotonic()
            try:
                await asyncio.wait_for(tab.verify_cf(click_delay=1, timeout=10), 30)
                res = "returned OK"
            except Exception as e:
                res = f"RAISED {type(e).__name__}: {str(e)[:160]!r}"
            await asyncio.sleep(0.3)
            print(f"{mode:22s} {res} after {time.monotonic()-t0:.2f}s | final url {tab.target.url}")
    finally:
        await browser.stop(); s.close()
asyncio.run(asyncio.wait_for(main(), 110))
