import asyncio, warnings
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<body><div id=wrap><p>x</p><my-list items='[1,2]'></my-list></div><br id=b clear=all></body>")
        await tab.sleep(0.5)
        wrap = await tab.select("#wrap")
        try:
            print("str(wrap):", str(wrap))
        except Exception as e:
            print("str(wrap) RAISES", type(e).__name__, e)
        br = await tab.select("#b")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            js = await br.get_js_attributes()
            print("get_js_attributes warnings:", [str(x.message).strip().splitlines()[0][:90] for x in w][:3])
        try:
            print("js.keys():", len(js.keys()))
        except Exception as e:
            print("js.keys() RAISES", type(e).__name__, e)
        try:
            js.clear(); print("js.clear() ok")
        except Exception as e:
            print("js.clear() RAISES", type(e).__name__, e)
    finally:
        await browser.stop()

asyncio.run(main())
