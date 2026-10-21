import asyncio, sys, os, glob, time, io
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import zendriver as zd
from helpers import serve
print("zendriver from", zd.__file__)
async def main():
    httpd, base = serve()
    browser = await zd.start(headless=True)
    d = os.path.join(HERE, "work", "shots"); os.makedirs(d, exist_ok=True); os.chdir(d)
    try:
        tab = await browser.get(base + "/docs/index.html")
        await tab.wait_for_ready_state("complete")
        paths = []; t0 = time.monotonic()
        for i in range(8):
            paths.append(await tab.save_screenshot())
        el = time.monotonic() - t0
        print("A7.10 8 calls in %.2fs, returned unique=%d, files on disk=%d" % (el, len(set(paths)), len(glob.glob('*.jpg'))))
    finally:
        await browser.stop(); httpd.shutdown()
asyncio.run(asyncio.wait_for(main(), 60))
# A7.8: Windows text mode simulation via TextIOWrapper(newline='\r\n') -- equivalent to newline=None when os.linesep == '\r\n'
b = io.BytesIO(); w = io.TextIOWrapper(b, encoding="ascii", newline="\r\n"); w.write("A: b\r\n\r\nX"); w.flush()
print("A7.8 text-mode on Windows writes", b.getvalue())
