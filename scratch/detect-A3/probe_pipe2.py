import asyncio, fcntl, termios, struct, sys
import zendriver as zd

def pending(f):
    buf = fcntl.ioctl(f.fileno(), termios.FIONREAD, b"\0\0\0\0")
    return struct.unpack("i", buf)[0]

async def main():
    b = await zd.start(headless=True, browser_args=["--enable-logging=stderr"])
    try:
        p = b._process
        print("stderr pending after start:", pending(p.stderr))
        tab = await b.get("about:blank")
        for i in range(6):
            try:
                await asyncio.wait_for(tab.evaluate("for (let i=0;i<300;i++) console.log('x'.repeat(100)+i); 1"), 10)
                print("round", i, "ok, stderr pending:", pending(p.stderr))
            except asyncio.TimeoutError:
                print("round", i, "TIMEOUT, stderr pending:", pending(p.stderr))
                break
        try:
            r = await asyncio.wait_for(tab.evaluate("1+1"), 10)
            print("simple evaluate:", r)
        except asyncio.TimeoutError:
            print("simple evaluate TIMEOUT: browser hung; pending", pending(p.stderr))
    finally:
        try:
            await asyncio.wait_for(b.stop(), 20)
        except asyncio.TimeoutError:
            print("stop timed out")
            b._process.kill()

asyncio.run(main())
