"""Q7 reproducer with an in-process fake CDP peer (no browser)."""
import asyncio
import json
import sys
import traceback

import websockets
from websockets.asyncio.server import serve

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection

print("zendriver from:", zendriver.__file__, "python", sys.version.split()[0], "websockets", websockets.__version__)

SENT = []  # methods received by the fake peer


async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        SENT.append(msg["method"])
        result = {}
        if msg["method"] == "Runtime.evaluate":
            result = {"result": {"type": "number", "value": 2}}
        await ws.send(json.dumps({"id": msg["id"], "result": result}))


def names(conn):
    return [m.__name__.rsplit(".", 1)[-1] for m in conn.enabled_domains]


async def scenario(port, second_domain_event, label):
    SENT.clear()
    conn = Connection(f"ws://127.0.0.1:{port}")
    h = lambda e: None
    h2 = lambda e: None
    conn.add_handler(cdp.network.RequestWillBeSent, h)
    await asyncio.wait_for(conn.send(cdp.runtime.evaluate("1")), 10)
    print(f"[{label}] after 1st send enabled_domains={names(conn)} peer saw={SENT}")
    conn.remove_handlers(cdp.network.RequestWillBeSent, h)
    conn.add_handler(second_domain_event, h2)
    SENT.clear()
    try:
        await asyncio.wait_for(conn.send(cdp.runtime.evaluate("1+1")), 10)
        print(f"[{label}] 2nd send OK")
    except Exception as e:
        print(f"[{label}] 2nd send RAISED: {type(e).__name__}: {e}")
        traceback.print_exc(limit=-4, file=sys.stdout)
    print(f"[{label}] peer saw during 2nd send: {SENT}  -> Runtime.evaluate sent? {'Runtime.evaluate' in SENT}")
    print(f"[{label}] enabled_domains now={names(conn)}")
    SENT.clear()
    try:
        await asyncio.wait_for(conn.send(cdp.runtime.evaluate("3")), 10)
        print(f"[{label}] 3rd send OK, peer saw {SENT}, enabled_domains={names(conn)}")
    except Exception as e:
        print(f"[{label}] 3rd send RAISED: {type(e).__name__}: {e}")
    await conn.aclose()


async def main():
    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        await scenario(port, cdp.log.EntryAdded, "A2.1 log")
        await scenario(port, cdp.runtime.ConsoleAPICalled, "B14.1 runtime")
        await scenario(port, cdp.page.LoadEventFired, "page")
        # control: second handler on an already-enabled domain -> no nested send
        await scenario(port, cdp.network.ResponseReceived, "control network")


asyncio.run(main())
