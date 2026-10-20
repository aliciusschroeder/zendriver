import asyncio, sys
import zendriver as zd
from zendriver import cdp

PAGE = "data:text/html,<div id=h></div><script>try{document.getElementById('h').attachShadow({mode:'closed'});document.title='OK'}catch(e){document.title='ERR:'+e.name+':'+e.message}</script>"

async def main(concurrent):
    browser = await zd.start(headless=True, expert=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        n = {"count": 0}
        orig = tab._send_oneshot
        async def counting(cdp_obj):
            tx_method = None
            r = await orig(cdp_obj)
            return r
        if concurrent:
            # public API that fans out concurrent sends on the fresh tab
            await tab.set_local_storage({"a": "1", "b": "2", "c": "3"})
        else:
            await tab.evaluate("1")
            await tab.evaluate("2")
        await tab.send(cdp.page.navigate(PAGE))
        await asyncio.sleep(1.5)
        title = await tab.evaluate("document.title")
        print("concurrent=%s title=%r" % (concurrent, title))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(sys.argv[1] == "1"), 50))
