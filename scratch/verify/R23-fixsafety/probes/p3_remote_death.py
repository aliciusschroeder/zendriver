# host/port browser whose remote dies and comes back: what does start() do?
import asyncio, sys, warnings, json, http
sys.path.insert(0, "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/R23-fixsafety/tests")
from test_r23_restart import FakeChrome
import zendriver as zd
print("zendriver from", zd.__file__)

async def main():
    chrome = await FakeChrome().__aenter__()
    port = chrome.port
    b = await zd.start(host="127.0.0.1", port=port, headless=False)
    print("connected; stopped:", b.stopped)
    # remote dies
    chrome.server.close(); await chrome.server.wait_closed()
    await asyncio.sleep(0.5)
    print("after remote death: stopped:", b.stopped, "conn.closed:", b.connection.closed, "listener running:", b.connection.listener.running)
    # remote comes back on same port
    chrome2 = FakeChrome()
    from websockets.asyncio.server import serve
    chrome2.port = port
    chrome2.server = await serve(chrome2._handler, "127.0.0.1", port, process_request=chrome2._process_request)
    old = b.connection
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            await asyncio.wait_for(b.start(), 20)
        except Exception as e:
            print("start raised", type(e).__name__, e)
    await asyncio.sleep(0.5)
    print("start() warnings:", [str(x.message) for x in w], "reconnected:", b.connection is not old, "open ws on new remote:", len(chrome2.open_websockets))
    try:
        await asyncio.wait_for(b.connection.send(zd.cdp.target.get_targets()), 5)
        print("send after start OK")
    except Exception as e:
        print("send after start failed:", type(e).__name__, e)
    await b.stop()
    await asyncio.wait_for(b.start(), 20)
    await asyncio.sleep(0.3)
    print("after stop()+start(): stopped:", b.stopped, "open ws:", len(chrome2.open_websockets))
    await b.stop()
    chrome2.server.close(); await chrome2.server.wait_closed()

asyncio.run(main())
