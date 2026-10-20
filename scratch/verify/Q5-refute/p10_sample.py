import array, asyncio, fcntl, os, sys, termios
import zendriver
def pending(f):
    buf = array.array("i", [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf, True); return buf[0]
async def main():
    b = await zendriver.start(headless=True)
    p = b._process
    await asyncio.sleep(2)
    os.read(p.stderr.fileno(), pending(p.stderr))
    for i in range(2):
        await b.main_tab.get("data:text/html,<canvas id=c></canvas><script>document.getElementById('c').getContext('webgl')</script>")
    await asyncio.sleep(1)
    n = pending(p.stderr)
    print(os.read(p.stderr.fileno(), n).decode()[:1500] if n else "nothing")
    await asyncio.wait_for(b.stop(), 30)
asyncio.run(main())
