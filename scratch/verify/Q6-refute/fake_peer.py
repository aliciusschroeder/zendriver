"""Fake CDP peer: burst of two matching RequestWillBeSent + responses, own-websocket path.

Usage: python fake_peer.py <trials> [gap_ms]
gap_ms > 0 sleeps between burst frames on the server side (spread events).
"""

import asyncio
import gc
import json
import sys

import websockets
from websockets.asyncio.server import serve

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection
from zendriver.core.expect import RequestExpectation

print("zendriver from", zendriver.__file__, "python", sys.version.split()[0], "websockets", websockets.__version__)

GAP = float(sys.argv[2]) / 1000 if len(sys.argv) > 2 else 0.0


def rwbs(rid, url):
    return {
        "method": "Network.requestWillBeSent",
        "params": {
            "requestId": rid,
            "loaderId": "L",
            "documentURL": "http://x/",
            "request": {"url": url, "method": "GET", "headers": {}, "initialPriority": "High", "referrerPolicy": "no-referrer"},
            "timestamp": 1.0,
            "wallTime": 1.0,
            "initiator": {"type": "other"},
            "redirectHasExtraInfo": False,
        },
    }


def rr(rid, url):
    return {
        "method": "Network.responseReceived",
        "params": {
            "requestId": rid,
            "loaderId": "L",
            "timestamp": 1.0,
            "type": "Fetch",
            "hasExtraInfo": False,
            "response": {
                "url": url, "status": 200, "statusText": "OK", "headers": {}, "mimeType": "application/json",
                "charset": "", "connectionReused": False, "connectionId": 1, "encodedDataLength": 1,
                "securityState": "secure",
            },
        },
    }


async def server_handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        await ws.send(json.dumps({"id": msg["id"], "result": {}}))
        if msg["method"] == "Network.enable":
            burst = [
                rwbs("R1", "http://x/a.json"),
                rwbs("R2", "http://x/b.json"),
                rr("R1", "http://x/a.json"),
                rr("R2", "http://x/b.json"),
            ]
            for m in burst:
                await ws.send(json.dumps(m))
                if GAP:
                    await asyncio.sleep(GAP)


async def one_trial(url):
    conn = Connection(url)
    try:
        async with RequestExpectation(conn, r".*\.json") as exp:
            await conn.send(cdp.network.enable())
            req = await asyncio.wait_for(exp.value, 5)
            resp = await asyncio.wait_for(exp.response_future, 5)
            return req.request.url, resp.response.url, exp.request_id
    finally:
        await conn.aclose()


async def main(trials):
    errors = []
    asyncio.get_running_loop().set_exception_handler(lambda l, c: errors.append(repr(c.get("exception"))))
    async with serve(server_handler, "127.0.0.1", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}"
        mism = 0
        for _ in range(trials):
            r, s, rid = await one_trial(url)
            if r.rsplit("/", 1)[-1] != s.rsplit("/", 1)[-1]:
                mism += 1
            last = (r, s, rid)
    gc.collect()
    await asyncio.sleep(0.05)
    gc.collect()
    print(f"gap_ms={GAP*1000:.0f} mismatches={mism}/{trials} last={last} lost_task_errors={len(errors)} {errors[:1]}")


asyncio.run(main(int(sys.argv[1])))
