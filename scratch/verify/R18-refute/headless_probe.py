"""R18 refute lens: B14.6. Does a detach during the first send's _prepare_headless leave
_prep_headless_done set so the HeadlessChrome UA leaks after reattach? And is the
UA override really dropped by Chrome when the session detaches (needed for a leak)?"""
import asyncio
import gc
import logging
import sys

import zendriver as zd
import zendriver.core.connection as zconn

print("zendriver from", zd.__file__, "python", sys.version.split()[0])

zombies = []
_orig_init = zconn.Listener.__init__


def spy_init(self, connection):
    if connection.websocket is None:
        zombies.append(connection)
    _orig_init(self, connection)


zconn.Listener.__init__ = spy_init

unhandled = []


def handler(loop, ctx):
    unhandled.append(ctx.get("message", "") + " " + repr(ctx.get("exception")))


async def ua(tab):
    await tab.reload()
    return await tab.evaluate("navigator.userAgent")


async def run(mode: str) -> None:
    asyncio.get_running_loop().set_exception_handler(handler)
    zombies.clear()
    unhandled.clear()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        if mode == "sequential":
            # prepare completes, then a normal aclose and reattach
            await tab.evaluate("1")
            await tab.aclose()
            first = "n/a"
        elif mode == "race":

            async def closer():
                while tab.session_id is None:
                    await asyncio.sleep(0)
                await tab.aclose()

            res = await asyncio.gather(tab.evaluate("1"), closer(), return_exceptions=True)
            first = f"{type(res[0]).__name__}: {str(res[0]).splitlines()[0] if str(res[0]) else ''}"
            print("   stale tx left in tab.mapper after race:", [(k, v.method, v.done()) for k, v in tab.mapper.items()])
        elif mode in ("closetarget", "closetarget_early"):
            async def closer():
                while mode == "closetarget" and tab.session_id is None:
                    await asyncio.sleep(0)
                await browser.connection.send(zd.cdp.target.close_target(tab.target_id))

            res = await asyncio.gather(tab.evaluate("1"), closer(), return_exceptions=True)
            print(f"mode={mode} first-send={res[0]!r:.80} flag={tab.__dict__.get('_prep_headless_done')}")
            await asyncio.sleep(0.5)
        if mode.startswith("closetarget"):
            pass
        else:
          flag_after_detach = tab.__dict__.get("_prep_headless_done")
          session_after_detach = tab.session_id
          u = await ua(tab)
          print(
            f"mode={mode:10s} first-send={first!r} session_after_detach={session_after_detach} "
            f"_prep_headless_done_after_detach={flag_after_detach} UA_after_reattach_has_Headless={'Headless' in u}"
          )
        # now prove Chrome drops the override on detach: send override by hand on a session,
        # detach, reattach WITHOUT override (bypass zendriver's prep by sending raw on browser conn)
    finally:
        await browser.stop()
    await asyncio.sleep(0.3)
    gc.collect()
    await asyncio.sleep(0.1)
    print(f"   zombie Listener() on detached connection: {len(zombies)}; unhandled loop errors: {len(unhandled)}")
    for u_ in unhandled[:4]:
        print("     ", u_[:160])


async def chrome_override_scope() -> None:
    """verify: an override set on session A does not survive A's detach (raw CDP, no zendriver prep)"""
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank", new_tab=True)
        bc = browser.connection
        tid = tab.target_id
        # raw sessions through the browser connection's flat-session plumbing would need routing;
        # use zendriver's own Tab but swap headless check off by making prep a no-op flag
        tab.__dict__["_prep_headless_done"] = True  # skip zendriver's override
        u0 = await ua(tab)
        await tab.send(zd.cdp.network.set_user_agent_override(user_agent="CustomUA/1.0"))
        u1 = await ua(tab)
        await tab.aclose()
        tab.__dict__["_prep_headless_done"] = True  # again skip zendriver's override on reattach
        u2 = await ua(tab)
        print(f"chrome check: no-override UA has Headless={'Headless' in u0}; with override={u1!r}; after detach+reattach (no override)={u2[:60]!r}... Headless={'Headless' in u2}")
    finally:
        await browser.stop()


async def main():
    for m in sys.argv[1:] or ["sequential", "race", "race", "race"]:
        if m == "scope":
            await asyncio.wait_for(chrome_override_scope(), 60)
        else:
            await asyncio.wait_for(run(m), 60)


asyncio.run(main())
