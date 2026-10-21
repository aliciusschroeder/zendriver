"""A1.6: cancelling the first command during attach leaks a chrome side session (real headless chromium)."""

import asyncio
import sys

import zendriver
from zendriver import cdp

print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)


async def main():
    browser = await zendriver.start(headless=True)
    try:
        attached = []
        detached = []
        browser.connection.add_handler(
            cdp.target.AttachedToTarget,
            lambda ev: attached.append((ev.session_id, ev.target_info.target_id)),
        )
        browser.connection.add_handler(
            cdp.target.DetachedFromTarget,
            lambda ev: detached.append(ev.session_id),
        )
        tab = await browser.get("about:blank", new_tab=True)
        tid = tab.target_id
        info = await browser.connection.send(cdp.target.get_target_info(tid))
        print("new tab session_id:", tab.session_id, "chrome attached flag before:", info.attached)

        # (1) the scenario from the claim: a short wait_for around the first command
        timeouts = 0
        for to in (1e-6, 1e-6, 1e-6):
            try:
                await asyncio.wait_for(tab.evaluate("1+1"), to)
                print(f"  wait_for({to}): completed (attach was fast)")
            except asyncio.TimeoutError:
                timeouts += 1
                print(f"  wait_for({to}): TimeoutError; tab.session_id after = {tab.session_id}")
        # (2) deterministic variant: cancel right after the attach request went out
        for i in range(2):
            if tab.session_id is not None:
                break
            t = asyncio.ensure_future(tab.evaluate("1+1"))
            await asyncio.sleep(0)  # first step runs: sends Target.attachToTarget, awaits reply
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                print(f"  cancel #{i}: CancelledError; tab.session_id after = {tab.session_id}")

        await asyncio.sleep(0.3)
        print("attached so far for tab:", [s for s, t in attached if t == tid])
        res = await asyncio.wait_for(tab.evaluate("1+1"), 10)
        print("evaluate after the cancels:", res, "tab.session_id now:", tab.session_id)
        await asyncio.wait_for(tab.aclose(), 10)
        await asyncio.sleep(0.5)
        tab_sessions = [s for s, t in attached if t == tid]
        orphans = [s for s in tab_sessions if s not in detached]
        print("attached:", tab_sessions)
        print("detached after tab.aclose():", detached)
        print("orphan sessions (attached, never detached):", orphans)
        info = await browser.connection.send(cdp.target.get_target_info(tid))
        print("chrome attached flag after tab.aclose():", info.attached)
        print("browser.connection._sessions:", list(browser.connection._sessions))
        # prove chrome still holds the orphans: detaching them explicitly succeeds
        for s in orphans:
            try:
                await browser.connection.send(cdp.target.detach_from_target(session_id=s))
                print("explicit Target.detachFromTarget(%s): succeeded (session was alive in chrome)" % s)
            except Exception as e:
                print("explicit detach of %s failed: %s" % (s, str(e).splitlines()[0]))
        await asyncio.sleep(0.3)
        info = await browser.connection.send(cdp.target.get_target_info(tid))
        print("chrome attached flag after explicit detach of orphans:", info.attached)
    finally:
        await browser.stop()


asyncio.run(main())
