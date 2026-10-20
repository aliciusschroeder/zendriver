import asyncio, pathlib, time
import zendriver as zd
SITE = pathlib.Path(__file__).parent / "site"
def url(n): return (SITE / n).as_uri()
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(url("dup.html"))
        await tab.wait_for_ready_state("complete")
        r = await tab.find_all("Login", timeout=1)
        print("find_all Login:", [(e.tag, e.backend_node_id) for e in r])
        r = await tab.find_all("needle", timeout=1)
        print("find_all needle:", [(e.tag, e.backend_node_id) for e in r])
        r = await tab.find_elements_by_text("   ", )
        print("find_elements_by_text blank:", len(r))
    finally:
        await browser.stop()
asyncio.run(main())
