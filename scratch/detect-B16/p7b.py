import asyncio, fcntl, termios, struct
import zendriver as zd

async def main():
    b = await zd.start(headless=True)
    def pending():
        return struct.unpack("I", fcntl.ioctl(b._process.stderr.fileno(), termios.FIONREAD, b"\0\0\0\0"))[0]
    print("after start:", pending())
    tab = b.main_tab
    for url in ["https://expired.badssl.com/", "https://127.0.0.1:1/", "http://nonexistent.invalid/"]:
        for i in range(5):
            try:
                await asyncio.wait_for(tab.get(url), 8)
            except Exception as e:
                pass
        print(url, "->", pending())
    data = b._process.stderr.read1(4000) if hasattr(b._process.stderr, "read1") else b""
    print(data[:1500].decode(errors="replace"))
    await b.stop()
asyncio.run(asyncio.wait_for(main(), 80))
