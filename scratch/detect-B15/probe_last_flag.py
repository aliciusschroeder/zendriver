import asyncio, zendriver as zd
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<div id=box><span>a</span><span>b</span></div>")
        await tab.wait_for_ready_state("complete")
        box = await tab.select("#box")
        for i in range(4):
            await tab.select("body")       # any tab-level query re-fetches the document
            spans = await box.query_selector_all("span")
            one = await box.query_selector("span") if i == 0 else "-"
            print(f"round {i}: box.query_selector_all('span') -> {len(spans)} elements;"
                  f" __last flag left on element: {getattr(box, '__last', None)}")
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 60))
