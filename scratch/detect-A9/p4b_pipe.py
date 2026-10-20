import asyncio, fcntl, termios, struct, sys, os
import zendriver as zd

def pending(f):
    buf = fcntl.ioctl(f.fileno(), termios.FIONREAD, struct.pack("i", 0))
    return struct.unpack("i", buf)[0]

async def main():
    b = await zd.start(headless=True)
    p = b._process
    print("after start:", pending(p.stderr))
    for i in range(20):
        t = await b.get("about:blank", new_tab=True)
        await t.close()
    await asyncio.sleep(1)
    print("after 20 new tabs:", pending(p.stderr))
    tab = b.main_tab
    for i in range(20):
        await tab.get("data:text/html,<audio autoplay src='data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA='></audio><video autoplay></video><canvas id=c></canvas><script>try{document.getElementById('c').getContext('webgl')}catch(e){}; navigator.geolocation&&navigator.geolocation.getCurrentPosition(()=>{},()=>{});</script>")
    await asyncio.sleep(1)
    print("after 20 media pages:", pending(p.stderr))
    for i in range(10):
        try:
            await asyncio.wait_for(tab.get("http://10.255.255.1/"), 3)
        except Exception: pass
    print("after unreachable:", pending(p.stderr))
    os.set_blocking(p.stderr.fileno(), False)
    data = os.read(p.stderr.fileno(), 70000).decode(errors="replace")
    lines = data.splitlines()
    print(len(lines), "lines; sample:")
    for l in lines[:8]: print("  ", l[:160])
    for l in lines[-5:]: print("  ", l[:160])
    await b.stop()

asyncio.run(asyncio.wait_for(main(), 140))
