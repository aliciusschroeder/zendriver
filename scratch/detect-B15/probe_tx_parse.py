import asyncio, json, logging
import websockets
from zendriver import cdp
from zendriver.core.connection import Connection

async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        if msg["method"] == "Target.getTargetInfo":
            # reply missing the required "targetInfo" key (e.g. a protocol mismatch)
            await ws.send(json.dumps({"id": msg["id"], "result": {}}))
        elif msg["method"] == "Browser.getVersion":
            await ws.send(json.dumps({"id": msg["id"], "result": {
                "protocolVersion": "1.3", "product": "x", "revision": "r",
                "userAgent": "ua", "jsVersion": "js"}}))
        elif msg["method"] == "Storage.getCookies":
            # a cookie whose sameSite enum value this cdp version doesn't know
            await ws.send(json.dumps({"id": msg["id"], "result": {"cookies": [{
                "name": "a", "value": "b", "domain": "d", "path": "/", "expires": -1,
                "size": 2, "httpOnly": False, "secure": False, "session": True,
                "priority": "Medium", "sameParty": False, "sourceScheme": "Secure",
                "sourcePort": 443, "sameSite": "SomeFutureValue"}]}}))
        else:
            await ws.send(json.dumps({"id": msg["id"], "result": {}}))

async def main():
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        conn = Connection(f"ws://127.0.0.1:{port}")
        for cmd in (cdp.target.get_target_info(), cdp.storage.get_cookies()):
            t = asyncio.create_task(conn.send(cmd))
            done, _ = await asyncio.wait({t}, timeout=3)
            print("send done within 3s:", bool(done), "| listener running:", conn.listener.running,
                  "| listener exc:", repr(conn.listener.task.exception()) if conn.listener.task.done() else None)
            if done:
                print("  result/exc:", repr(t.exception() if t.exception() else t.result())[:120])
            else:
                print("  stuck at:"); t.print_stack(limit=3)
                t.cancel()
        # the connection itself still works for a fresh command (a new listener is created)
        r = await asyncio.wait_for(conn.send(cdp.browser.get_version()), 3)
        print("next send ok:", r[0])
        await conn.aclose()

asyncio.run(main())
