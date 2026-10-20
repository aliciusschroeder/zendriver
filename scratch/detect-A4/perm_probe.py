import asyncio
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException

async def main():
    b = await zd.start(headless=True)
    try:
        bad = []
        for p in cdp.browser.PermissionType:
            try:
                await b.connection.send(cdp.browser.grant_permissions([p]))
            except ProtocolException as e:
                bad.append((p.value, str(e).splitlines()[0][:80]))
        print("rejected individually:", bad)
    finally:
        await b.stop()
asyncio.run(main())
