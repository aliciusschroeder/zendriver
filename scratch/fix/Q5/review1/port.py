import asyncio
import logging
import socket
import time

import zendriver as zd
from zendriver.core import util

records: list[str] = []


class H(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        records.append(record.getMessage())


logging.getLogger("zendriver").addHandler(H())
logging.getLogger("zendriver").setLevel(logging.INFO)


async def main() -> None:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    util.free_port = lambda: port  # type: ignore[assignment]
    t0 = time.monotonic()
    try:
        await zd.start(headless=True)
        print("unexpected: started")
    except Exception as e:
        print("start failed after %.1fs: %s" % (time.monotonic() - t0, str(e).split("\n")[2].strip()))
    for m in records:
        if m.startswith("Browser stderr"):
            print("LOGGED len", len(m), "devtools line present", "Cannot start http server for devtools" in m)
            print(m[:300].replace("\n", " | "))


asyncio.run(main())
