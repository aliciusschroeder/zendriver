import asyncio, fcntl, termios, struct, sys
import zendriver as zd

def avail(f):
    return struct.unpack("i", fcntl.ioctl(f.fileno(), termios.FIONREAD, b"\0\0\0\0"))[0]

async def main():
    browser = await zd.start(headless=True)
    p = browser._process
    print("after start", avail(p.stderr), flush=True)
    for i in range(20):
        t = await asyncio.wait_for(browser.get("about:blank", new_tab=True), 10)
        await asyncio.wait_for(t.close(), 10)
    print("after 20 new/close tabs", avail(p.stderr), flush=True)
    tab = browser.main_tab
    for i in range(20):
        try:
            await asyncio.wait_for(tab.get(f"https://127.0.0.1:{1+i}/"), 10)
        except Exception as e:
            print("err", type(e))
    print("after 20 failed navs", avail(p.stderr), flush=True)
    for i in range(20):
        await asyncio.wait_for(tab.get("data:text/html,<video src='http://127.0.0.1:9/x.mp4' autoplay></video><img src='http://127.0.0.1:9/x.png'>"), 10)
    print("after 20 media navs", avail(p.stderr), flush=True)
    data = p.stderr.read(avail(p.stderr)).decode(errors="replace")
    print(data[-3000:])
    import threading
    threading.Thread(target=lambda: p.stderr.read(), daemon=True).start()
    await asyncio.wait_for(browser.stop(), 30)
asyncio.run(main())
