"""Q6 browser-free reproducer: a fake CDP peer sends bursts of matching events.

Scenarios (selected by the Page.navigate url the client sends):
  expect   : requestWillBeSent R1(a.json), R2(b.json), responseReceived R1, R2,
             loadingFinished R1, R2 -- all written back-to-back.
  fetch    : two Fetch.requestPaused back-to-back (BaseFetchInterception)
  download : two Browser.downloadWillBegin back-to-back (DownloadExpectation)
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
from zendriver.core.intercept import BaseFetchInterception


def req(rid, url):
    return {
        "method": "Network.requestWillBeSent",
        "params": {
            "requestId": rid,
            "loaderId": "L1",
            "documentURL": "http://x/",
            "request": {
                "url": url,
                "method": "GET",
                "headers": {},
                "initialPriority": "High",
                "referrerPolicy": "no-referrer",
            },
            "timestamp": 1.0,
            "wallTime": 1.0,
            "initiator": {"type": "script"},
            "redirectHasExtraInfo": False,
            "type": "Fetch",
        },
    }


def resp(rid, url):
    return {
        "method": "Network.responseReceived",
        "params": {
            "requestId": rid,
            "loaderId": "L1",
            "timestamp": 2.0,
            "type": "Fetch",
            "hasExtraInfo": False,
            "response": {
                "url": url,
                "status": 200,
                "statusText": "OK",
                "headers": {},
                "mimeType": "application/json",
                "charset": "",
                "connectionReused": False,
                "connectionId": 1,
                "encodedDataLength": 10,
                "securityState": "neutral",
            },
        },
    }


def lf(rid):
    return {
        "method": "Network.loadingFinished",
        "params": {"requestId": rid, "timestamp": 3.0, "encodedDataLength": 10},
    }


def paused(rid, url):
    return {
        "method": "Fetch.requestPaused",
        "params": {
            "requestId": rid,
            "request": {
                "url": url,
                "method": "GET",
                "headers": {},
                "initialPriority": "High",
                "referrerPolicy": "no-referrer",
            },
            "frameId": "F1",
            "resourceType": "Fetch",
            "responseStatusCode": 200,
        },
    }


def dl(guid):
    return {
        "method": "Browser.downloadWillBegin",
        "params": {
            "frameId": "F1",
            "guid": guid,
            "url": f"http://x/{guid}.bin",
            "suggestedFilename": f"{guid}.bin",
        },
    }


SCENARIOS = {
    "scenario://expect": [
        req("R1", "http://x/a.json"),
        req("R2", "http://x/b.json"),
        resp("R1", "http://x/a.json"),
        resp("R2", "http://x/b.json"),
        lf("R1"),
        lf("R2"),
    ],
    "scenario://fetch": [paused("P1", "http://x/a.json"), paused("P2", "http://x/b.json")],
    "scenario://download": [dl("G1"), dl("G2")],
}

received_methods = []


async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        received_methods.append(msg["method"])
        result = {}
        if msg["method"] == "Network.getResponseBody":
            rid = msg["params"]["requestId"]
            result = {"body": f"body of {rid}", "base64Encoded": False}
        elif msg["method"] == "Page.navigate":
            result = {"frameId": "F1"}
        await ws.send(json.dumps({"id": msg["id"], "result": result}))
        if msg["method"] == "Page.navigate":
            for ev in SCENARIOS[msg["params"]["url"]]:
                await ws.send(json.dumps(ev))


async def main():
    print("python", sys.version.split()[0], "websockets", websockets.__version__, "zendriver", zendriver.__file__)
    loop = asyncio.get_running_loop()
    errors = []
    loop.set_exception_handler(lambda l, c: errors.append(repr(c.get("exception"))))

    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}/devtools/page/X")

        # --- expect_request / expect_response ---
        for kind in ("request", "response"):
            errors.clear()
            from zendriver.core.expect import RequestExpectation, ResponseExpectation

            cls = RequestExpectation if kind == "request" else ResponseExpectation
            async with cls(conn, r"http://x/.*\.json") as exp:
                await conn.send(cdp.page.navigate("scenario://expect"))
                r = await asyncio.wait_for(exp.request_future, 5)
                s = await asyncio.wait_for(exp.response_future, 5)
                body, _ = await asyncio.wait_for(exp.response_body, 5)
                v = await asyncio.wait_for(exp.value, 5)
            await asyncio.sleep(0.2)
            gc.collect()
            await asyncio.sleep(0.05)
            vurl = v.request.url if kind == "request" else v.response.url
            print(
                f"[{kind}] .request url={r.request.url} ({r.request_id})  exp.request_id={exp.request_id}  "
                f".response url={s.response.url} ({s.request_id})  body={body!r}  .value url={vurl}"
            )
            print(f"[{kind}] mismatch={r.request_id != s.request_id}  lost task errors={errors}")

        # --- BaseFetchInterception ---
        errors.clear()
        fi = BaseFetchInterception(conn, "*", cdp.fetch.RequestStage.RESPONSE, cdp.network.ResourceType.FETCH)
        async with fi:
            await conn.send(cdp.page.navigate("scenario://fetch"))
            ev = await asyncio.wait_for(fi.response_future, 5)
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.2)
        gc.collect()
        await asyncio.sleep(0.05)
        print(f"[fetch-intercept] got {ev.request_id} url={ev.request.url}  lost task errors={errors}")

        # --- DownloadExpectation ---
        errors.clear()
        from zendriver.core.expect import DownloadExpectation

        de = DownloadExpectation(conn)
        async with de:
            await conn.send(cdp.page.navigate("scenario://download"))
            ev = await asyncio.wait_for(de.value, 5)
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.2)
        gc.collect()
        await asyncio.sleep(0.05)
        print(f"[download] got guid={ev.guid}  lost task errors={errors}")

        await conn.aclose()


asyncio.run(asyncio.wait_for(main(), 60))
