import asyncio
import zendriver as zd
from zendriver import cdp

async def main():
    b = await zd.start(headless=True)
    tab = await b.get("data:text/html,<div id=a><p>hi <b>there</b></p></div>")
    await tab.wait_for_ready_state("complete")
    div = await tab.select("#a")
    print("outerHTML:", await div.get_html())
    print("html_from_tree(div):", await zd.util.html_from_tree(div, tab))
    print("circle(100, 0) first point:", next(zd.util.circle(100, 0)), " circle(100, 1) first point:", next(zd.util.circle(100, 1)))
    await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
