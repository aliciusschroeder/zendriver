import asyncio, json, pathlib
import zendriver as zd
URL = pathlib.Path("page.html").resolve().as_uri()
async def main():
    b = await zd.start(headless=True)
    try:
        tab = await b.get(URL); await tab.wait_for_ready_state("complete")
        ta = await tab.select("#ta")
        for s in ["👍", "👍🏽", "🇺🇸", "👨‍👩‍👧", "é", "क्षि"]:
            await tab.evaluate("document.getElementById('ta').value=''")
            try:
                await ta.send_keys("x" + s + "y")
                v = await tab.evaluate("document.getElementById('ta').value")
                print(repr(s), "utf16 units:", len(s.encode('utf-16-le'))//2, "-> ok, value matches:", v == "x" + s + "y", json.dumps(v))
            except Exception as e:
                v = await tab.evaluate("document.getElementById('ta').value")
                print(repr(s), "utf16 units:", len(s.encode('utf-16-le'))//2, "->", type(e).__name__, str(e).splitlines()[0], "| value so far:", json.dumps(v))
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
