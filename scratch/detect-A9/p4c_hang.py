import asyncio, fcntl, termios, struct, sys, os, time
import zendriver as zd

def pending(f):
    buf = fcntl.ioctl(f.fileno(), termios.FIONREAD, struct.pack("i", 0))
    return struct.unpack("i", buf)[0]

PAGE = "data:text/html,<canvas id=c></canvas><script>var g=document.getElementById('c').getContext('webgl');g&&g.clear(g.COLOR_BUFFER_BIT);document.title='ok'+(!!g)</script>"

async def main(drain):
    b = await zd.start(headless=True)
    p = b._process
    if drain:
        # drain stderr in a background thread, like a fixed implementation would
        import threading
        threading.Thread(target=lambda: [None for _ in iter(lambda: p.stderr.read1(65536), b"")], daemon=True).start()
    tab = b.main_tab
    for i in range(400):
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(tab.get(PAGE), 10)
            title = await asyncio.wait_for(tab.evaluate("document.title"), 10)
            await asyncio.wait_for(tab.screenshot_b64(), 10)
        except asyncio.TimeoutError:
            print(f"iteration {i}: TIMEOUT (hang) stderr pending={pending(p.stderr) if not drain else 'drained'}")
            break
        if i % 50 == 0:
            print(f"iteration {i}: ok title={title} stderr pending={pending(p.stderr) if not drain else 'drained'} dt={time.monotonic()-t0:.2f}")
    else:
        print("completed 400 iterations without hang")
    p.kill()
    await b.stop()

asyncio.run(asyncio.wait_for(main(sys.argv[1] == "1"), 400))
