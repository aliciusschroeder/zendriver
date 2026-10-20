import asyncio, sys, zendriver
async def main():
    b = await zendriver.start(headless=True)
    try:
        tab = b.main_tab
        for expr in ["'\\ud800'", "'a\\udfffb'", "String.fromCharCode(0xD83D)"]:
            r = await asyncio.wait_for(tab.evaluate(expr), 5)
            print(expr, "->", ascii(r), "| browser listener running:", b.connection.listener.running)
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
