import asyncio, sys, time
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
async def main():
    b = await zd.start(headless=True)
    try:
        _, _, rev, ua, _ = await b.connection.send(cdp.browser.get_version())
        print("chrome:", ua)
        try:
            await asyncio.wait_for(b.grant_all_permissions(), 15)
            print("grant_all_permissions OK")
        except Exception as e:
            print("grant_all_permissions:", type(e).__name__, str(e).splitlines()[0])
        rejected = []
        for p in cdp.browser.PermissionType:
            try:
                await b.connection.send(cdp.browser.grant_permissions([p]))
            except Exception as e:
                rejected.append((p.value, str(e).splitlines()[0][:70]))
        print("rejected singly:", rejected)
        # with an origin
        rej2 = []
        for p in cdp.browser.PermissionType:
            try:
                await b.connection.send(cdp.browser.grant_permissions([p], origin="https://example.com"))
            except Exception as e:
                rej2.append(p.value)
        print("rejected singly with origin:", rej2)
        # iteration with all tabs closed
        for t in list(b.tabs):
            await t.close()
        await asyncio.sleep(0.5)
        await b.update_targets()
        print("targets after closing all:", [(t.type_, t.url) for t in b.targets])
        try:
            print("list(browser):", list(b))
        except Exception as e:
            print("list(browser):", type(e).__name__, e)
    finally:
        await b.stop()
asyncio.run(main())
