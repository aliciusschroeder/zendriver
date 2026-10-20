import asyncio
import sys

import zendriver as zd
from zendriver.core.connection import Connection

which = sys.argv[1]


async def main():
    if which == "browser":
        ctx = zd.Browser(zd.Config(headless=True))  # not started, no process
    elif which == "connection":
        ctx = Connection("ws://127.0.0.1:9/never")  # never connected; aclose is a no-op
    else:
        ctx = None
    if ctx is None:
        sys.exit(3)
    async with ctx:
        sys.exit(3)


asyncio.run(main())
