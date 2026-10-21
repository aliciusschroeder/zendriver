"""real headless chromium: scraping loops over select/find/xpath/wait_for are
cancelled at random moments; every task must end cancelled promptly, with no
leftover tasks and no asyncio error logs."""

import asyncio
import logging
import random
import shutil
import sys

import zendriver as zd

logged: list[str] = []


class H(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            logged.append(record.getMessage()[:200])


logging.getLogger("asyncio").addHandler(H())


async def main() -> None:
    print("python", sys.version.split()[0], zd.__file__)
    browser = await zd.start(
        headless=True, sandbox=False, browser_executable_path=shutil.which("chromium")
    )
    try:
        tab = await browser.get(
            "data:text/html,<div id=x>hello world</div><p>other</p>"
        )
        await tab.select("#x", timeout=5)
        calls = {
            "select": lambda: tab.select("#x", timeout=5),
            "select_missing": lambda: tab.select("#nope", timeout=2),
            "find": lambda: tab.find("hello world", timeout=5),
            "find_all": lambda: tab.find_all("hello", timeout=5),
            "xpath": lambda: tab.xpath("//div", timeout=2),
            "wait_for": lambda: tab.wait_for(selector="#x", timeout=5),
        }
        rng = random.Random(1)
        bad = []
        for i in range(120):
            name = rng.choice(list(calls))
            call = calls[name]

            async def loop_forever() -> None:
                while True:
                    await call()

            t = asyncio.create_task(loop_forever())
            await asyncio.sleep(rng.uniform(0, 0.08))
            t.cancel()
            done, _ = await asyncio.wait({t}, timeout=5)
            if not t.cancelled():
                bad.append((i, name, t.done(), t.done() and repr(t.exception())))
        await asyncio.sleep(0.2)
        left = [
            t
            for t in asyncio.all_tasks()
            if t is not asyncio.current_task() and "_poll" in repr(t)
        ]
        print("not cancelled:", bad)
        print("leftover poll tasks:", len(left))
        # the tab still works afterwards
        el = await tab.select("#x", timeout=5)
        print("select afterwards:", el.text)
    finally:
        await browser.stop()
    print("asyncio error logs:", logged)


asyncio.run(main())
