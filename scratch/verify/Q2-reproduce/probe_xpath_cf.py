"""A5.7 (xpath timeout<=0 / busy spin) and A11.4 (verify_cf overshoot) on real Chromium."""
import asyncio
import os
import signal
import sys
import time

import zendriver
from zendriver.core import cloudflare

print("zendriver imported from", zendriver.__file__, "python", sys.version.split()[0], flush=True)

PAGE = "data:text/html,<html><body><p id=topp>hello world</p></body></html>"

CF_PAGE = (
    "data:text/html,<html><body>"
    "<div id=host style='width:300px;height:80px'></div>"
    "<input name=cf-turnstile-response type=hidden>"
    "<script>"
    "const r=document.getElementById('host').attachShadow({mode:'closed'});"
    "r.innerHTML='<iframe src=\"about:blank%23challenges.cloudflare.com\" style=\"width:300px;height:65px;border:0\"></iframe>';"
    "</script></body></html>"
)


async def main():
    browser = await zendriver.start(headless=True)
    pid = browser._process_pid
    try:
        tab = await browser.get(PAGE)
        await tab.wait_for_ready_state("complete", timeout=5)

        # ---- A5.7: xpath with timeout 0 / negative / default
        for to in (2.5, 0, -1, 0.001):
            t0 = time.monotonic()
            res = await asyncio.wait_for(tab.xpath("//p[@id='topp']", timeout=to), 15)
            print(f"[A5.7] xpath(//p[@id='topp'], timeout={to}) -> {res!r} in {time.monotonic()-t0:.3f}s", flush=True)

        # count sends during a miss with timeout=0.5
        counts = {}
        orig_send = tab.send

        async def counting_send(cdp_obj, _is_update=False):
            # peek the method name
            gen = cdp_obj
            try:
                req = next(gen)
                name = req["method"]
            except StopIteration:
                name = "?"
            counts[name] = counts.get(name, 0) + 1

            def regen():
                resp = yield req
                try:
                    gen.send(resp)
                except StopIteration as si:
                    return si.value

            return await orig_send(regen(), _is_update)

        tab.send = counting_send
        t0 = time.monotonic()
        res = await asyncio.wait_for(tab.xpath("//nope", timeout=0.5), 15)
        el = time.monotonic() - t0
        tab.send = orig_send
        print(f"[A5.7] xpath miss timeout=0.5 -> {res!r} in {el:.3f}s; sends: total={sum(counts.values())} {counts}", flush=True)

        # ---- A11.4: verify_cf overshoot on an unsolvable (fake) challenge
        tab2 = await browser.get(CF_PAGE)
        await tab2.wait_for_ready_state("complete", timeout=5)
        present = await asyncio.wait_for(cloudflare.cf_is_interactive_challenge_present(tab2, timeout=2), 15)
        print("[A11.4] fake challenge detected:", present, flush=True)
        for timeout, delay in ((1, 4), (2, 0.1)):
            clicks = 0
            orig_click = tab2.mouse_click

            async def counting_click(*a, **k):
                nonlocal clicks
                clicks += 1
                return await orig_click(*a, **k)

            tab2.mouse_click = counting_click
            t0 = time.monotonic()
            try:
                await asyncio.wait_for(tab2.verify_cf(click_delay=delay, timeout=timeout), 30)
                r = "returned None"
            except Exception as e:
                r = f"raised {type(e).__name__}: {e}"
            print(f"[A11.4] verify_cf(timeout={timeout}, click_delay={delay}) {r} after {time.monotonic()-t0:.2f}s clicks={clicks}", flush=True)
            del tab2.mouse_click
    finally:
        try:
            await asyncio.wait_for(browser.stop(), 20)
        except Exception as e:
            print("stop failed", e)
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass


asyncio.run(main())
