import asyncio, zendriver as zd
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<p>Hello world</p><button>go</button>")
        await tab.wait_for_ready_state("complete")
        print("tab.wait_for(text=...) ->", await tab.wait_for(text="Hello world", timeout=2))
        try:
            print("tab(text=...) ->", await tab(text="Hello world", timeout=2))
        except asyncio.TimeoutError as e:
            print("tab(text='Hello world') -> TimeoutError:", e)
        try:
            print("tab(selector='button') ->", await tab(selector="button", timeout=2))
        except asyncio.TimeoutError as e:
            print("tab(selector='button') -> TimeoutError:", e)
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 60))
