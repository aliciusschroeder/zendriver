import asyncio, fcntl, termios, array, sys, os, time
import zendriver

def pending(f):
    if f is None:
        return None
    buf = array.array("i", [0])
    fcntl.ioctl(f.fileno(), termios.FIONREAD, buf)
    return buf[0]

async def main():
    print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
    args = sys.argv[1:] or ["--enable-logging=stderr"]
    b = await zendriver.start(headless=True, browser_args=args)
    pid = b._process.pid
    print("chrome pid", pid, "stderr pending after start", pending(b._process.stderr))
    tab = b.main_tab
    hung = False
    for i in range(300):
        try:
            await asyncio.wait_for(tab.evaluate("console.log('x'.repeat(1000)); 1+1"), 10)
        except asyncio.TimeoutError:
            print(f"round {i}: TIMEOUT, stderr pending {pending(b._process.stderr)}")
            try:
                print("wchan", open(f"/proc/{pid}/wchan").read())
            except Exception as e:
                print("wchan err", e)
            hung = True
            break
        if i % 20 == 0:
            print(f"round {i} ok, pending {pending(b._process.stderr)}")
    if hung:
        try:
            await asyncio.wait_for(b.connection.send(zendriver.cdp.browser.get_version()), 5)
            print("browser getVersion OK")
        except asyncio.TimeoutError:
            print("browser getVersion TIMEOUT")
    t0 = time.time()
    try:
        await asyncio.wait_for(b.stop(), 30)
        print("stop ok in %.1fs" % (time.time() - t0))
    except asyncio.TimeoutError:
        print("stop TIMEOUT; killing pid", pid)
        os.kill(pid, 9)
    print("RESULT hung=", hung)

asyncio.run(main())
