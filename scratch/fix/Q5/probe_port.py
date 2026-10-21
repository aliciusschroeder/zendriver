import asyncio, logging, socket
import zendriver as zd
from zendriver.core import util

records: list[str] = []

class H(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        records.append(record.getMessage())

async def main() -> None:
    logging.getLogger("zendriver").addHandler(H())
    logging.getLogger("zendriver").setLevel(logging.INFO)
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    util.free_port = lambda: port  # type: ignore
    try:
        await zd.start(headless=True, browser_connection_max_tries=4)
    except Exception as e:
        print("start failed:", str(e).strip().splitlines()[1])
    for r in records:
        if r.startswith("Browser stderr"):
            print("LOGGED:", "devtools line present" if "Cannot start http server for devtools" in r else repr(r[:200]), "len", len(r))

asyncio.run(main())
