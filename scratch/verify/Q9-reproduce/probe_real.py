"""Real headless Chromium reproducer for Q9."""

import asyncio
import json
import os
import sys

import zendriver as zd
from zendriver import cdp
from zendriver.core.connection import ProtocolException

print("zendriver from:", zd.__file__, "python", sys.version.split()[0])


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # zombie check
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("State:"):
                    return "Z" not in line
    except FileNotFoundError:
        return False
    return True


async def main():
    started = []

    # 1. JSONDecodeError in `async with await zd.start() as browser:`
    browser = None
    try:
        async with await zd.start(headless=True) as browser:
            started.append(browser)
            json.loads("{bad")
    except json.JSONDecodeError as e:
        print("[real Browser] json -> except json.JSONDecodeError matched:", e)
    except Exception as e:
        print(f"[real Browser] json -> caller sees {type(e).__name__}: {e}")
    pid = browser._process_pid
    print(
        f"[real Browser] after block: browser.stopped={browser.stopped} pid={pid} alive={alive(pid)}"
    )

    # 2. TaskGroup failure in the block
    b2 = await zd.start(headless=True)
    started.append(b2)

    async def boom():
        raise ValueError("inner")

    try:
        async with b2:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(boom())
    except* ValueError as eg:
        print("[real Browser] taskgroup -> except* ValueError matched", eg)
    except* Exception as eg:
        print(
            "[real Browser] taskgroup -> except* ValueError MISSED; got",
            [f"{type(x).__name__}: {x}" for x in eg.exceptions],
        )

    # 3. real ProtocolException inside `async with tab:` and `async with browser:`
    tab = b2.main_tab
    orig = None
    try:
        async with tab:
            try:
                await tab.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
            except ProtocolException as e:
                orig = e
                print(f"[real Tab] inside block code={e.code!r}")
                raise
    except ProtocolException as e:
        print(
            f"[real Tab] caller sees ProtocolException code={e.code!r} same_obj={e is orig} msg_tail={str(e)[-40:]!r}"
        )

    tab2 = await b2.get("about:blank", new_tab=True)
    orig = None
    try:
        async with b2:
            try:
                await tab2.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
            except ProtocolException as e:
                orig = e
                print(f"[real Browser] inside block code={e.code!r}")
                raise
    except ProtocolException as e:
        print(
            f"[real Browser] caller sees ProtocolException code={e.code!r} same_obj={e is orig}"
        )

    for b in started:
        await b.stop()
    for b in started:
        print("cleanup: pid", b._process_pid, "alive after stop:", alive(b._process_pid) if b._process_pid else None)


asyncio.run(asyncio.wait_for(main(), 90))
