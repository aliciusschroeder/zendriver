import asyncio, fcntl, termios, struct, sys
import zendriver as zd

def pending(f):
    buf = fcntl.ioctl(f.fileno(), termios.FIONREAD, b"\0\0\0\0")
    return struct.unpack("i", buf)[0]

async def main():
    b = await zd.start(headless=True)
    try:
        p = b._process
        print("stderr pending after start:", pending(p.stderr), "stdout:", pending(p.stdout))
        tab = await b.get("about:blank")
        for i in range(5):
            await tab.evaluate("for (let i=0;i<2000;i++) console.error('x'.repeat(200)+i)")
            await asyncio.sleep(0.3)
            print("after console spam", i, "stderr pending:", pending(p.stderr))
        # navigate to unreachable pages, which chrome may log
        for i in range(5):
            try:
                await asyncio.wait_for(b.get(f"http://127.0.0.1:1/{i}"), 5)
            except Exception as e:
                print("nav err", type(e).__name__)
        print("after navs stderr pending:", pending(p.stderr))
    finally:
        await asyncio.wait_for(b.stop(), 20)

asyncio.run(main())
