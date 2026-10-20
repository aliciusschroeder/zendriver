"""A11.4: verify_cf timeout overrun by click_delay, real headless Chromium,
local fake turnstile-like page (shadow root iframe + light-DOM response input)."""
import asyncio
import sys
import time

import zendriver
from zendriver.core import cloudflare as cfmod

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])

HTML = """<html><body>
<div id='host'></div>
<input type='hidden' name='cf-turnstile-response' value=''>
<script>
const r = document.getElementById('host').attachShadow({mode: 'closed'});
r.innerHTML = "<iframe data-src='https://challenges.cloudflare.com/x' style='width:300px;height:65px;border:1px solid red' srcdoc='<p>chk</p>'></iframe>";
</script></body></html>"""


async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = browser.main_tab
        import base64
        url = "data:text/html;base64," + base64.b64encode(HTML.encode()).decode()
        await tab.get(url)
        await asyncio.sleep(0.5)
        print("challenge present:", await cfmod.cf_is_interactive_challenge_present(tab, timeout=2))
        clicks = []
        orig = tab.mouse_click

        async def counting_click(*a, **k):
            clicks.append(time.monotonic())
            return await orig(*a, **k)

        tab.mouse_click = counting_click
        for timeout, delay in ((1, 4), (2, 0.1), (15, 5)):
            clicks.clear()
            t0 = time.monotonic()
            try:
                await asyncio.wait_for(tab.verify_cf(click_delay=delay, timeout=timeout), 40)
                res = "returned"
            except TimeoutError as e:
                res = f"TimeoutError({str(e)[:50]})"
            print(f"verify_cf(timeout={timeout}, click_delay={delay}): {res} after {time.monotonic()-t0:.2f}s, clicks={len(clicks)}")
    finally:
        await browser.stop()


asyncio.run(main())
