"""Probe M: Browser.stop() right after chrome dies. Tab.aclose() only catches
ProtocolException around its Target.detachFromTarget round trip, so a
ConnectionClosed from the dying websocket escapes and aborts Browser._stop."""
import asyncio
import os
import sys

import zendriver as zd


async def once(i: int, sleep_before_stop: float) -> None:
    browser = await zd.start(headless=True)
    tab = await browser.get("about:blank")
    await tab.evaluate("1 + 1")
    assert tab.session_id is not None
    data_dir = browser.config.user_data_dir
    pid = browser._process_pid
    browser._process.kill()
    if sleep_before_stop:
        await asyncio.sleep(sleep_before_stop)
    try:
        await asyncio.wait_for(browser.stop(), 20)
        print(i, "stop ok; process cleared:", browser._process is None,
              "profile removed:", not os.path.exists(data_dir))
    except asyncio.TimeoutError:
        print(i, "stop HUNG")
    except BaseException as e:
        print(i, "stop RAISED", type(e).__name__, e,
              "| _process still set:", browser._process is not None,
              "| profile dir still exists:", os.path.exists(data_dir))
        # clean up for the next round
        browser._process = None
        browser._process_pid = None
        await browser._cleanup_temporary_profile()


async def main() -> None:
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0
    for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 5):
        await once(i, delay)


asyncio.run(main())
