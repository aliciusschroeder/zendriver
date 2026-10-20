import asyncio, fcntl, termios, struct, sys
import zendriver as zd

def pending(f):
    buf = fcntl.ioctl(f.fileno(), termios.FIONREAD, struct.pack("i", 0))
    return struct.unpack("i", buf)[0]

def pipesz(f):
    F_GETPIPE_SZ = 1032
    return fcntl.fcntl(f.fileno(), F_GETPIPE_SZ)

async def main(n):
    b = await zd.start(headless=True)
    p = b._process
    print("pipe capacity:", pipesz(p.stderr))
    print("after start: stderr pending", pending(p.stderr), "stdout pending", pending(p.stdout))
    tab = b.main_tab
    for i in range(n):
        await tab.get("data:text/html,<script>console.error('x'.repeat(100))</script><h1>%d</h1>" % i)
    await tab.sleep(1)
    print(f"after {n} navigations: stderr pending", pending(p.stderr), "stdout pending", pending(p.stdout))
    await b.stop()

asyncio.run(asyncio.wait_for(main(int(sys.argv[1])), 120))
