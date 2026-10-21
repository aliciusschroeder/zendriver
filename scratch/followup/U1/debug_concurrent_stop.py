"""concurrent Browser.stop(): print where an unretrieved Transaction was created"""

import asyncio
import gc
import shutil
import sys
import traceback

import zendriver as zd

CHROME = shutil.which("chromium")


async def main() -> None:
    print(sys.version.split()[0], zd.__file__)
    loop = asyncio.get_running_loop()
    loop.slow_callback_duration = 10
    found = []

    def handler(loop, context):
        fut = context.get("future")
        tb = context.get("source_traceback") or getattr(fut, "_source_traceback", None)
        exc = context.get("exception")
        found.append(
            (
                context["message"],
                repr(exc),
                "".join(traceback.format_list(tb[-12:])) if tb else "no tb",
            )
        )

    loop.set_exception_handler(handler)
    for i in range(6):
        b = await zd.start(headless=True, sandbox=False, browser_executable_path=CHROME)
        await b.get("data:text/html,<p>x</p>")
        r = await asyncio.wait_for(
            asyncio.gather(b.stop(), b.stop(), return_exceptions=True), 60
        )
        del b
        gc.collect()
        await asyncio.sleep(0.1)
        gc.collect()
        print(f"run {i}: results={r} errors={len(found)}")
        for message, exc, tb in found:
            print(" ", message, exc)
            print(tb)
        found.clear()


asyncio.run(main(), debug=True)
