import asyncio, json, sys
import zendriver as zd
from zendriver.core.connection import Connection, ProtocolException

async def body(kind):
    if kind == "json":
        json.loads("{not json")
    if kind == "group":
        async with asyncio.TaskGroup() as tg:
            async def boom(): raise ValueError("inner")
            tg.create_task(boom())
    if kind == "proto":
        raise ProtocolException({"code": -32000, "message": "No node with given id found"})

async def main():
    print(sys.version.split()[0])
    browser = await zd.start(headless=True)
    try:
        for kind in ("json", "group", "proto"):
            try:
                async with browser:
                    await body(kind)
            except* Exception as eg:
                for e in eg.exceptions:
                    print(f"[Browser] {kind}: caller sees {type(e).__name__}: {str(e)[:90]!r}",
                          "code=" + str(getattr(e, "code", "-")))
            # Tab (Connection.__aexit__) path
        tab = browser.main_tab
        try:
            async with tab:
                json.loads("{not json")
        except Exception as e:
            print(f"[Tab] json: caller sees {type(e).__name__}: {e}")
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 60))
