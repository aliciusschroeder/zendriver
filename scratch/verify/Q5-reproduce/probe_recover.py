import asyncio, fcntl, os, struct, sys, termios, time
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0], flush=True)
def pending(f):
    return struct.unpack("i", fcntl.ioctl(f.fileno(), termios.FIONREAD, struct.pack("i", 0)))[0]
async def main():
    b = await zd.start(headless=True, browser_args=["--enable-logging=stderr"])
    p = b._process; tab = b.main_tab
    for i in range(1500):
        try:
            await asyncio.wait_for(tab.evaluate("console.log('y'.repeat(100)); 1"), 5)
        except asyncio.TimeoutError:
            print(f"evaluate #{i} TIMEOUT, pending={pending(p.stderr)}, browser wchan={open(f'/proc/{p.pid}/wchan').read()}", flush=True)
            break
    else:
        print("no hang"); 
    os.set_blocking(p.stderr.fileno(), False)
    total = 0
    try:
        while True:
            total += len(os.read(p.stderr.fileno(), 65536))
    except BlockingIOError:
        pass
    print("drained", total, "bytes from stderr pipe (test harness, not zendriver)", flush=True)
    t = time.monotonic()
    r = await asyncio.wait_for(tab.evaluate("1+1"), 10)
    print(f"evaluate after drain -> {r} in {time.monotonic()-t:.2f}s", flush=True)
    # keep draining so stop() works
    async def drain():
        while True:
            try:
                if not os.read(p.stderr.fileno(), 65536):
                    return
            except BlockingIOError:
                await asyncio.sleep(0.05)
            except OSError:
                return
    d = asyncio.ensure_future(drain())
    await asyncio.wait_for(b.stop(), 30); d.cancel()
    print("stop ok", flush=True)
asyncio.run(main())
