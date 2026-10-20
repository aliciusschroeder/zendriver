import asyncio, sys, time, fcntl, termios, array, os
import zendriver as zd

def pending(f):
    buf = array.array('i', [0])
    fcntl.ioctl(f.fileno(), termios.FIONREAD, buf)
    return buf[0]

def pipesize(f):
    return fcntl.fcntl(f.fileno(), 1032)  # F_GETPIPE_SZ

async def main():
    args = sys.argv[1:]
    browser = await zd.start(headless=True, browser_args=args)
    try:
        p = browser._process
        print("pipe size", pipesize(p.stderr), "stderr pending after start", pending(p.stderr), "stdout pending", pending(p.stdout))
        tab = browser.main_tab
        for i in range(400):
            try:
                await asyncio.wait_for(tab.get(f"data:text/html,<p>{i}</p><script>console.log('x'.repeat(500))</script>"), 10)
                await asyncio.wait_for(tab.evaluate("1+1"), 10)
            except asyncio.TimeoutError:
                print(f"iteration {i}: TIMEOUT - stderr pending {pending(p.stderr)}")
                # check whether browser responds at all
                try:
                    v = await asyncio.wait_for(browser.connection.send(zd.cdp.browser.get_version()), 5)
                    print("browser process still answers Browser.getVersion")
                except asyncio.TimeoutError:
                    print("browser process does NOT answer Browser.getVersion")
                break
            if i % 50 == 0:
                print(i, "stderr pending", pending(p.stderr), "stdout pending", pending(p.stdout))
        print("final stderr pending", pending(p.stderr))
    finally:
        try:
            await asyncio.wait_for(browser.stop(), 15)
        except Exception as e:
            print("stop failed", type(e).__name__, e)
            if browser._process: browser._process.kill()

asyncio.run(main())
