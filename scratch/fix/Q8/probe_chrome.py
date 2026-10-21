import asyncio

import zendriver as zd

HTML = (
    "data:text/html,<body><div id=wrap><my-list items='[1,2]'></my-list></div>"
    "<br id=b clear=all><span id=s get=g></span>"
    "<a items=3 href='http://x.example/a'>x</a></body>"
)


async def main() -> None:
    print("zendriver from", zd.__file__)
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(HTML)
        br = await tab.select("#b")
        await br.update()
        print("br.update OK", br, br.attrs)
        print("str(wrap)", str(await tab.select("#wrap")))
        s = await tab.select("#s")
        print("span get", s.get("id"), s["id"], s.get("get"))
        print("urls", await tab.get_all_urls())
        js = await br.get_js_attributes()
        js.clear()
        print("js.clear OK", len(js))
    finally:
        await browser.stop()


asyncio.run(main())
