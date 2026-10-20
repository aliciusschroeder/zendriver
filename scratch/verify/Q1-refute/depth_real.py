import asyncio, json, sys, websockets, zendriver
async def main():
    browser = await zendriver.start(headless=True)
    try:
        async with websockets.connect(browser.connection.websocket_url, max_size=2**28) as ws:
            i = 0
            async def raw(method, params=None, session=None):
                nonlocal i; i += 1
                m = {"id": i, "method": method, "params": params or {}}
                if session: m["sessionId"] = session
                await ws.send(json.dumps(m))
                while True:
                    txt = await asyncio.wait_for(ws.recv(), 20)
                    r = json.loads(txt)
                    if r.get("id") == i: return r, txt
            t = [x for x in (await raw("Target.getTargets"))[0]["result"]["targetInfos"] if x["type"] == "page"][0]
            s = (await raw("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True}))[0]["result"]["sessionId"]
            for n in (100, 200, 290, 295, 296, 297, 298, 299, 300, 301, 400, 500):
                expr = f"(()=>{{let a=[],c=a;for(let i=1;i<{n};i++){{c.push([]);c=c[0]}};return a}})()"
                r, txt = await raw("Runtime.evaluate", {"expression": expr, "returnByValue": True}, s)
                ok = "error" not in r and "exceptionDetails" not in r["result"]
                print(n, "chrome returned value" if ok else ("error: " + str(r.get("error") or r["result"].get("exceptionDetails", {}).get("text"))[:60]))
                if ok:
                    open(f"msg_{n}.json", "w").write(txt)
            # same via the deep object path a user might hit: deep linked list
            expr = "(()=>{let h={v:0},c=h;for(let i=1;i<990;i++){c.next={v:i};c=c.next};return h})()"
            r, txt = await raw("Runtime.evaluate", {"expression": expr, "returnByValue": True}, s)
            print("linked list 990:", "value" if "error" not in r and "exceptionDetails" not in r["result"] else "error")
            open("msg_list990.json", "w").write(txt)
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 80))
