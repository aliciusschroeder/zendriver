import array, asyncio, fcntl, os, sys, termios, time
import zendriver
print("zendriver from", zendriver.__file__, sys.version.split()[0], flush=True)
def pending(f):
    buf = array.array("i", [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf, True); return buf[0]
async def main():
    b = await zendriver.start(headless=True)
    print("udd", b.config.user_data_dir, flush=True)
    t0 = time.monotonic()
    DUR = float(sys.argv[1])
    while time.monotonic() - t0 < DUR:
        print("t=%4.0fs stderr pending %d" % (time.monotonic() - t0, pending(b._process.stderr)), flush=True)
        await asyncio.sleep(30)
    data = os.read(b._process.stderr.fileno(), 1 << 20)
    import re, collections
    c = collections.Counter(re.findall(r":(?:ERROR|WARNING):([^\]]+)\]", data.decode("utf-8","replace")))
    print(c.most_common(10), flush=True)
    await asyncio.wait_for(b.stop(), 30)
    print("stopped", flush=True)
asyncio.run(main())
