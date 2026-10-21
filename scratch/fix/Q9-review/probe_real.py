import asyncio
import json
import sys

import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

print(
    "zendriver from",
    zd.__file__,
    "| py",
    sys.version.split()[0],
    "| Tab.__aexit__ is Connection.__aexit__:",
    zd.Tab.__aexit__ is Connection.__aexit__,
)


async def main() -> None:
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        original = None
        try:
            async with tab:
                try:
                    await tab.send(
                        cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999))
                    )
                except ProtocolException as e:
                    original = e
                    raise
        except ProtocolException as e:
            print(
                "tab/protocol:",
                type(e).__name__,
                "code=",
                e.code,
                "same_obj=",
                e is original,
            )

        tab = await browser.get("about:blank", new_tab=True)
        if sys.version_info >= (3, 11):

            async def boom() -> None:
                raise ValueError("inner")

            try:
                async with tab:
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(boom())
            except* ValueError as eg:
                print("tab/taskgroup: except* ValueError matched", eg.exceptions)
            except* Exception as eg:
                print("tab/taskgroup: MISSED", eg.exceptions)

        # cancellation through the block: asyncio.timeout must still turn it into TimeoutError
        tab = await browser.get("about:blank", new_tab=True)
        try:
            async with asyncio.timeout(0.3) if sys.version_info >= (3, 11) else _null():
                async with tab:
                    await asyncio.sleep(5)
        except (asyncio.TimeoutError, TimeoutError) as e:
            print("tab/timeout:", type(e).__name__)

        try:
            await asyncio.wait_for(_with_tab_sleep(browser), 0.3)
        except asyncio.TimeoutError as e:
            print("tab/wait_for:", type(e).__name__)

        try:
            async with browser:
                json.loads("{bad")
        except json.JSONDecodeError as e:
            print("browser/json:", type(e).__name__, e.pos)

        t3 = await browser.get("about:blank", new_tab=True)
        print("browser usable after:", await t3.evaluate("1+1"))
    finally:
        await browser.stop()


class _null:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *a: object) -> None:
        return None


async def _with_tab_sleep(browser: zd.Browser) -> None:
    tab = await browser.get("about:blank", new_tab=True)
    async with tab:
        await asyncio.sleep(5)


asyncio.run(asyncio.wait_for(main(), 90))
