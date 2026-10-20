import asyncio, os, sys, time
import zendriver as zd

async def main():
    args = sys.argv[1:]
    b = await zd.start(headless=True, browser_args=args)
    pid = b._process_pid
    def stderr_pending():
        # bytes sitting unread in the stderr pipe
        import fcntl, termios, struct
        buf = fcntl.ioctl(b._process.stderr.fileno(), termios.FIONREAD, b"\0\0\0\0")
        return struct.unpack("I", buf)[0]
    tab = b.main_tab
    t0 = time.time()
    for i in range(200):
        try:
            await asyncio.wait_for(tab.evaluate(f"console.log('x'.repeat(2000)); {i}"), 5)
        except asyncio.TimeoutError:
            print(f"evaluate #{i} timed out after {time.time()-t0:.1f}s; unread stderr bytes={stderr_pending()}; process alive={b._process.poll() is None}")
            break
    else:
        print("200 evaluates ok; unread stderr bytes:", stderr_pending())
    t1 = time.time()
    try:
        await asyncio.wait_for(b.stop(), 15)
        print(f"stop ok in {time.time()-t1:.1f}s")
    except asyncio.TimeoutError:
        print(f"browser.stop() did not finish within 15s; chrome pid {pid} alive={os.path.exists(f'/proc/{pid}')}")
        os.kill(pid, 9)

asyncio.run(main())
