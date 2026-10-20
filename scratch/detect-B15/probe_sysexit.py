import asyncio, sys
import zendriver as zd

class FakeBrowser:  # Browser.__aexit__ never touches self
    __aenter__ = zd.Browser.__aenter__
    __aexit__ = zd.Browser.__aexit__

async def main():
    async with FakeBrowser():
        sys.exit(3)

asyncio.run(main())
