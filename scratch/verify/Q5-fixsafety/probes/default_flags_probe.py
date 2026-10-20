import asyncio, fcntl, termios, array, sys, os, time, shutil
import zendriver

def pending(f):
    buf = array.array("i", [0]); fcntl.ioctl(f.fileno(), termios.FIONREAD, buf); return buf[0]

async def handle(reader, writer):
    try:
        await reader.read(100)
        writer.write(b"HTTP/1.0 400 nope\r\n\r\n"); await writer.drain()
    finally:
        writer.close()

async def main():
    print("zendriver from", zendriver.__file__)
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    srv = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = srv.sockets[0].getsockname()[1]
    b = await zendriver.start(headless=True)
    pid = b._process.pid
    udd = b.config.user_data_dir
    print("after start pending", pending(b._process.stderr))
    tab = b.main_tab
    t0 = time.time(); hung = False
    for i in range(N):
        try:
            await asyncio.wait_for(tab.send(zendriver.cdp.page.navigate(f"https://127.0.0.1:{port}/{i}")), 10)
            await asyncio.wait_for(tab.evaluate("1+1"), 10)
        except asyncio.TimeoutError:
            print(f"iteration {i}: TIMEOUT pending {pending(b._process.stderr)} after {time.time()-t0:.0f}s; wchan {open(f'/proc/{pid}/wchan').read()}")
            hung = True
            break
        if i % 25 == 0 or i < 3:
            print(f"iteration {i} pending {pending(b._process.stderr)} t={time.time()-t0:.0f}s")
    try:
        await asyncio.wait_for(b.stop(), 20)
    except asyncio.TimeoutError:
        print("stop timeout; killing my chrome", pid); os.kill(pid, 9); await asyncio.sleep(1)
        shutil.rmtree(udd, ignore_errors=True)
    srv.close()
    print("RESULT hung", hung)

asyncio.run(main())
