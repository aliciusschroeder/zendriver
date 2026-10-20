import asyncio, sys
import zendriver
from zendriver.core.connection import Connection
async def main():
    c = Connection("ws://127.0.0.1:1/devtools/browser/x")
    if sys.argv[1] == "cm":
        async with c:
            sys.exit(3)
    else:
        sys.exit(3)
asyncio.run(main())
