import array, asyncio, fcntl, os, sys, termios
import zendriver
print("zendriver from", zendriver.__file__, sys.version.split()[0], flush=True)
def pending(f):
    buf = array.array("i", [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf, True); return buf[0]
async def main():
    b = await zendriver.start(headless=True, browser_args=["--enable-logging=stderr"])
    p = b._process
    print("start pending", pending(p.stderr), flush=True)
    for i in range(80):
        try:
            await asyncio.wait_for(b.main_tab.evaluate("console.log('x'.repeat(%s)); 1" % sys.argv[1]), 5)
        except asyncio.TimeoutError:
            print("evaluate #%d TIMEOUT; pending %d" % (i, pending(p.stderr)), flush=True); break
    else:
        print("no hang; pending", pending(p.stderr), flush=True)
    os.read(p.stderr.fileno(), 1<<20)
    await asyncio.wait_for(b.stop(), 30); print("stopped", flush=True)
asyncio.run(main())
