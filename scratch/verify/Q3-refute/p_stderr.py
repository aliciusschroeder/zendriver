import asyncio, os, sys, signal, shutil, fcntl, termios, struct
import zendriver as zd
def queued(f):
    return struct.unpack("i", fcntl.ioctl(f.fileno(), termios.FIONREAD, b"\0\0\0\0"))[0]
async def main():
    b = await zd.start(headless=True)
    pid = b._process_pid; udd = b.config.user_data_dir
    try:
        print("after start: stderr bytes queued", queued(b._process.stderr))
        tab = await b.get("about:blank")
        for i in range(20):
            await tab.get("data:text/html,<script>console.error('x'.repeat(100))</script><p>%d</p>" % i)
        await asyncio.sleep(1)
        print("after 20 navigations: stderr bytes queued", queued(b._process.stderr))
        for i in range(5):
            t = await b.get("about:blank", new_tab=True)
        await asyncio.sleep(1)
        print("after 5 new tabs: stderr bytes queued", queued(b._process.stderr))
        await b.stop()
    finally:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        shutil.rmtree(udd, ignore_errors=True)
asyncio.run(main())
