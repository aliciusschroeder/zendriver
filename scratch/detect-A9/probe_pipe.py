import asyncio, fcntl, termios, struct, sys, time
import zendriver as zd

def avail(f):
    buf = fcntl.ioctl(f.fileno(), termios.FIONREAD, b"\0\0\0\0")
    return struct.unpack("i", buf)[0]

async def main(extra):
    browser = await zd.start(headless=True, browser_args=extra)
    p = browser._process
    print("after start: stderr bytes pending", avail(p.stderr), "stdout", avail(p.stdout), flush=True)
    tab = browser.main_tab
    for i in range(400):
        try:
            await asyncio.wait_for(tab.get(f"data:text/html,<p>{i}</p><script>console.error('x'.repeat(200))</script>"), 10)
            r = await asyncio.wait_for(tab.evaluate("1+1"), 10)
        except asyncio.TimeoutError:
            print(f"iteration {i}: TIMEOUT, stderr pending={avail(p.stderr)}", flush=True)
            try:
                print("wchan:", open(f"/proc/{p.pid}/wchan").read(), flush=True)
            except Exception as e:
                print(e)
            break
        if i % 20 == 0:
            print(f"iteration {i}: ok r={r} stderr pending={avail(p.stderr)}", flush=True)
    else:
        print("all iterations ok, stderr pending", avail(p.stderr))
    # drain so stop works
    import threading
    threading.Thread(target=lambda: p.stderr.read(), daemon=True).start()
    threading.Thread(target=lambda: p.stdout.read(), daemon=True).start()
    await asyncio.wait_for(browser.stop(), 30)

extra = sys.argv[1:]
asyncio.run(main(extra))
