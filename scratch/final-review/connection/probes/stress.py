"""Stress the connection/listener state machine with flat sessions:
concurrent tab sends, one-shot receive errors (Q1 break + revival), parse
failures, handler errors, detaches/re-attaches, cancellations (Q12),
and domain auto-enables with handler churn (Q7). Checks: never two concurrent
recv() on the websocket, at most one live listener task per connection, no
duplicated event dispatch, enabled_domains without duplicates, nothing hangs."""
import asyncio, sys, logging, random, collections, itertools
import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import Connection, Listener
from fakews import FakeWS, use, tab_for, listener_tasks

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 0
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
rnd = random.Random(SEED)

seen_events = collections.Counter()
ev_seq = itertools.count(1)
sessions = itertools.count(1)
problems = []

async def main():
    attached = {}  # session id -> target id
    def script(cmd):
        m = cmd["method"]
        frames = []
        if m == "Target.attachToTarget":
            sid = f"S{next(sessions)}"
            attached[sid] = cmd["params"]["targetId"]
            return [{"id": cmd["id"], "result": {"sessionId": sid}}]
        if m == "Target.detachFromTarget":
            sid = cmd["params"]["sessionId"]
            attached.pop(sid, None)
            return ["REPLY", {"method": "Target.detachedFromTarget",
                              "params": {"sessionId": sid}}]
        sid = cmd.get("sessionId")
        if sid is not None and sid not in attached:
            return [{"id": cmd["id"], "sessionId": sid,
                     "error": {"code": -32001, "message": "Session with given id not found."}}]
        r = rnd.random()
        if sid is not None and r < 0.5:
            # some events for that session
            for _ in range(rnd.randint(1, 3)):
                frames.append({"method": "Page.frameStoppedLoading", "sessionId": sid,
                               "params": {"frameId": f"F{next(ev_seq)}"}})
        r = rnd.random()
        if r < 0.03:
            frames.append(RuntimeError("cannot receive"))  # Q1 break, reply stays queued
            frames.append("REPLY")
        elif r < 0.05:
            frames.append("not json")
            frames.append("REPLY")
        elif r < 0.07:
            return frames  # never answered
        elif r < 0.09 and sid is not None:
            # browser-initiated detach of this session (e.g. target crashed)
            attached.pop(sid, None)
            frames.append({"method": "Target.detachedFromTarget", "params": {"sessionId": sid}})
            frames.append("REPLY")
        else:
            frames.append("REPLY")
        return frames

    ws = FakeWS(results={"Runtime.evaluate": {"result": {"type": "number", "value": 2}}},
                script=script)
    use(ws)
    bc = Connection("ws://fake/devtools/browser/x")
    tabs = [tab_for(bc, f"T{i}") for i in range(4)]

    def handler(event, tab):
        seen_events[event.frame_id] += 1

    async def op(tab):
        k = rnd.random()
        try:
            if k < 0.45:
                await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), rnd.choice([0.05, 0.3, 2]))
            elif k < 0.6:
                await asyncio.wait_for(tab.send(cdp.runtime.evaluate("1")), 2)
            elif k < 0.7:
                if handler not in tab.handlers.get(cdp.page.FrameStoppedLoading, []):
                    tab.add_handler(cdp.page.FrameStoppedLoading, handler)
                await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
            elif k < 0.78:
                tab.remove_handlers(cdp.page.FrameStoppedLoading)
                ev = rnd.choice([cdp.network.RequestWillBeSent, cdp.log.EntryAdded, cdp.runtime.ConsoleAPICalled])
                if handler not in tab.handlers.get(ev, []):
                    tab.add_handler(ev, handler)
                await asyncio.wait_for(tab.send(cdp.page.bring_to_front()), 2)
            elif k < 0.85:
                await asyncio.wait_for(tab.aclose(), 2)
            elif k < 0.92:
                await asyncio.wait_for(bc.send(cdp.target.set_discover_targets(True)), 2)
            else:
                t = asyncio.ensure_future(tab.send(cdp.page.bring_to_front()))
                await asyncio.sleep(rnd.choice([0, 0.001, 0.01]))
                t.cancel()
                try:
                    await asyncio.wait_for(t, 2)
                except asyncio.CancelledError:
                    pass
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        except Exception as e:
            pass

    def check(where):
        # at most one live listener per connection
        per_conn = collections.Counter()
        for t in listener_tasks():
            lst = t.get_coro().cr_frame.f_locals.get("self") if t.get_coro().cr_frame else None
            if lst is not None:
                per_conn[id(lst.connection)] += 1
        for cid, n in per_conn.items():
            if n > 1:
                names = [c for c in [bc] + tabs if id(c) == cid]
                problems.append(f"{where}: {n} live listeners for {names[0].websocket_url if names else cid}")
        for c in [bc] + tabs:
            if len(set(map(id, c.enabled_domains))) != len(c.enabled_domains):
                problems.append(f"{where}: duplicate enabled_domains {c.enabled_domains}")
        if ws.max_concurrent_recv > 1:
            problems.append(f"{where}: concurrent recv {ws.max_concurrent_recv}")
            ws.max_concurrent_recv = 1

    for i in range(ROUNDS):
        await asyncio.wait_for(asyncio.gather(*(op(rnd.choice(tabs)) for _ in range(rnd.randint(1, 6)))), 30)
        await asyncio.sleep(0)
        check(f"round {i}")

    dup = {k: v for k, v in seen_events.items() if v > 1}
    if dup:
        problems.append(f"duplicated events: {list(dup.items())[:5]}")
    # final health: every tab can still talk
    for t in tabs:
        try:
            await asyncio.wait_for(t.send(cdp.page.bring_to_front()), 3)
        except asyncio.TimeoutError:
            # an unanswered reply on purpose is possible; retry once
            try:
                await asyncio.wait_for(t.send(cdp.page.bring_to_front()), 3)
            except Exception as e:
                problems.append(f"final send on {t.target_id} failed twice: {e!r}")
        except Exception:
            pass
    for t in tabs:
        try:
            await asyncio.wait_for(t.aclose(), 3)
        except Exception:
            pass
    await bc.aclose()
    await asyncio.sleep(0.3)
    live = listener_tasks()
    if live:
        problems.append(f"{len(live)} listener tasks still alive after closing everything")
    print(f"seed={SEED} events={sum(seen_events.values())} sent={len(ws.sent)} problems={len(problems)}")
    for p in problems[:20]:
        print("  PROBLEM", p)

logging.basicConfig(level=logging.CRITICAL)
asyncio.run(main())
