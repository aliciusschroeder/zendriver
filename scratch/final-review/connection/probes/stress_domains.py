"""Q7 guard + Q12 undo under concurrency: random handler churn, concurrent sends,
cancellations at random points (incl. during nested Domain.enable), slow/unanswered
enables, enable errors and Q1 receive errors. Invariant after a final clean send:
every domain in enabled_domains has really been enabled on the fake for the
current session (else its events are silently never delivered), no duplicates,
and every handler domain is enabled."""
import asyncio, sys, logging, random, collections, itertools
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection
from fakews import FakeWS, use, tab_for

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 0
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
rnd = random.Random(SEED)
import os
NOANS = float(os.environ.get("NOANS", "0.08"))
REMOVE = float(os.environ.get("REMOVE", "0.2"))
DOMAIN_EVENTS = [cdp.network.RequestWillBeSent, cdp.log.EntryAdded, cdp.runtime.ConsoleAPICalled,
                 cdp.page.LoadEventFired, cdp.dom.DocumentUpdated, cdp.css.StyleSheetAdded]
problems = []

async def main():
    sessions = itertools.count(1)
    enabled_on_fake = collections.defaultdict(set)  # sid -> {"Network",...}
    faulty = {"on": True}
    loop = asyncio.get_running_loop()
    ws_holder = {}

    def script(cmd):
        m = cmd["method"]
        if m == "Target.attachToTarget":
            return [{"id": cmd["id"], "result": {"sessionId": f"S{next(sessions)}"}}]
        sid = cmd.get("sessionId")
        dom, _, act = m.partition(".")
        if faulty["on"]:
            r = rnd.random()
            if act == "enable" and r < NOANS:
                return []  # never answered
            if act == "enable" and r < NOANS + 0.04:
                return [{"id": cmd["id"], "sessionId": sid, "error": {"code": -32000, "message": "nope"}}]
            if r < 0.02:
                return [RuntimeError("cannot receive"), "REPLY"]
            if act == "enable" and r < NOANS + 0.3:
                # answer later
                async def later():
                    await asyncio.sleep(rnd.choice([0.001, 0.01, 0.05]))
                    if act == "enable": enabled_on_fake[sid].add(dom)
                    ws_holder["ws"].frames.put_nowait(ws_holder["ws"].reply_for(cmd))
                loop.create_task(later())
                return []
        if act == "enable": enabled_on_fake[sid].add(dom)
        if act == "disable": enabled_on_fake[sid].discard(dom)
        return None

    ws = FakeWS(script=script); ws_holder["ws"] = ws
    use(ws)
    bc = Connection("ws://fake/devtools/browser/x")
    tabs = [tab_for(bc, f"T{i}") for i in range(3)]
    def h(e): pass

    async def op(tab):
        k = rnd.random()
        try:
            if k < 0.35:
                ev = rnd.choice(DOMAIN_EVENTS)
                if h not in tab.handlers.get(ev, []): tab.add_handler(ev, h)
            elif k < 0.35 + REMOVE:
                ev = rnd.choice(DOMAIN_EVENTS)
                tab.remove_handlers(ev)
            if rnd.random() < 0.3:
                t = asyncio.ensure_future(tab.send(cdp.page.bring_to_front()))
                for _ in range(rnd.randint(0, 6)): await asyncio.sleep(0)
                t.cancel()
                await asyncio.wait({t}, timeout=5)
                if not t.done(): problems.append("cancelled send did not finish")
            else:
                await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), rnd.choice([0.005, 0.02, 0.2, 1]))
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        except Exception:
            pass

    for i in range(ROUNDS):
        await asyncio.wait_for(asyncio.gather(*(op(rnd.choice(tabs)) for _ in range(rnd.randint(1, 5)))), 30)

    # settle: no more faults, let delayed replies land, then one clean send per tab
    faulty["on"] = False
    await asyncio.sleep(0.2)
    for tab in tabs:
        await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 5)
        sid = tab.session_id
        names = [d.__name__.rsplit(".", 1)[-1] for d in tab.enabled_domains]
        if len(set(names)) != len(names):
            problems.append(f"{tab.target_id}: duplicate enabled_domains {names}")
        fake = {d.lower() for d in enabled_on_fake[sid]}
        for n in names:
            if n not in fake:
                problems.append(f"{tab.target_id}: '{n}' in enabled_domains but never enabled on the browser (fake has {sorted(fake)})")
        wanted = set()
        for ev, hs in tab.handlers.items():
            if hs:
                mod = ev.__module__.rsplit(".", 1)[-1]
                wanted.add(mod)
        missing = wanted - set(names)
        if missing:
            problems.append(f"{tab.target_id}: handler domains not enabled after a clean send: {missing} (enabled {names})")
    for t in tabs: await t.aclose()
    await bc.aclose()
    print(f"seed={SEED} sent={len(ws.sent)} problems={len(problems)}")
    for p in problems[:10]: print("  PROBLEM", p)

logging.basicConfig(level=logging.CRITICAL)
asyncio.run(main())
