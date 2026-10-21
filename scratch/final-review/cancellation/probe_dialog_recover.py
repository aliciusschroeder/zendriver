"""
Real headless chromium: page with an open alert(); a handler for a domain that
is not enabled yet is added; a bounded Q2 call times out; then the user tries to
recover by dismissing the dialog with Page.handleJavaScriptDialog.

usage: python probe_dialog_recover.py <domain: log|runtime|network|page|none> <api: select|find|xpath|wait_for>
"""

import asyncio
import logging
import os
import sys
import time

import zendriver as zd
from zendriver import cdp

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

HANDLERS = {
    "log": (cdp.log.EntryAdded, cdp.log),
    "runtime": (cdp.runtime.ConsoleAPICalled, cdp.runtime),
    "network": (cdp.network.RequestWillBeSent, cdp.network),
    "page": (cdp.page.FrameNavigated, cdp.page),
    "none": (None, None),
}


def dump(tab: zd.Tab, label: str) -> None:
    pending = {k: (v.method, v.done()) for k, v in tab.mapper.items()}
    print(
        f"  [{label}] enabled_domains={[m.__name__.split('.')[-1] for m in tab.enabled_domains]}"
        f" manual={[m.__name__.split('.')[-1] for m in tab.manually_enabled_domains]}"
        f" mapper={pending}",
        flush=True,
    )


async def main() -> None:
    domain = sys.argv[1]
    api = sys.argv[2]
    print("python", sys.version.split()[0], "zendriver", zd.__file__, flush=True)
    browser = await zd.start(
        headless=True,
        sandbox=False,
        browser_executable_path=os.environ["CHROME"],
    )
    pid = browser._process_pid
    print("chrome pid", pid, flush=True)
    try:
        tab = browser.main_tab
        assert tab is not None
        await tab.get("data:text/html,<p id=hello>hello</p>")
        await tab.select("#hello", timeout=5)
        if os.environ.get("PAGE_ENABLE", "1") == "1":
            await tab.send(cdp.page.enable())
        dump(tab, "before alert")
        await tab.evaluate("setTimeout(() => alert('blocked'), 50)")
        await asyncio.sleep(0.5)

        event_type, _ = HANDLERS[domain]
        if event_type is not None:
            tab.add_handler(event_type, lambda e: None)

        t0 = time.monotonic()
        try:
            if api == "select":
                r = await tab.select("#nope", timeout=1)
            elif api == "find":
                r = await tab.find("nope-text", timeout=1)
            elif api == "xpath":
                r = await tab.xpath("//nope", timeout=1)
            elif api == "wait_for":
                r = await tab.wait_for(selector="#nope", timeout=1)
            print(f"  first call returned {r!r} after {time.monotonic()-t0:.2f}s", flush=True)
        except asyncio.TimeoutError as e:
            print(f"  first call TimeoutError after {time.monotonic()-t0:.2f}s: {e}", flush=True)
        dump(tab, "after timeout")

        # recovery: dismiss the dialog
        t0 = time.monotonic()
        try:
            await asyncio.wait_for(
                tab.send(cdp.page.handle_java_script_dialog(accept=True)), 8
            )
            print(f"  handleJavaScriptDialog OK after {time.monotonic()-t0:.2f}s", flush=True)
        except asyncio.TimeoutError:
            print(f"  handleJavaScriptDialog HUNG (safety net 8s) after {time.monotonic()-t0:.2f}s", flush=True)
        except Exception as e:
            print(f"  handleJavaScriptDialog raised {type(e).__name__}: {e} after {time.monotonic()-t0:.2f}s", flush=True)
        dump(tab, "after dismiss")

        t0 = time.monotonic()
        try:
            el = await asyncio.wait_for(tab.select("#hello", timeout=3), 10)
            print(f"  next select -> {el!r} after {time.monotonic()-t0:.2f}s", flush=True)
        except BaseException as e:
            print(f"  next select raised {type(e).__name__}: {e} after {time.monotonic()-t0:.2f}s", flush=True)
        dump(tab, "end")
    finally:
        t0 = time.monotonic()
        await asyncio.wait_for(browser.stop(), 60)
        print(f"  stop took {time.monotonic()-t0:.2f}s, process gone: {browser._process is None}", flush=True)


asyncio.run(main())
