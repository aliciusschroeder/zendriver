import asyncio, sys, os, fcntl, termios, array
import zendriver as zd
def pending(f):
    buf = array.array('i', [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf); return buf[0]
async def main():
    browser = await zd.start(headless=True)
    p = browser._process
    await asyncio.sleep(1)
    n = pending(p.stderr)
    os.set_blocking(p.stderr.fileno(), False)
    print(os.read(p.stderr.fileno(), n).decode()[:3000])
    await browser.stop()
asyncio.run(main())
