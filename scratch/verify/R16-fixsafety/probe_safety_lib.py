import asyncio, json, sys, types
sys.path.insert(0, sys.argv[1])
import websockets
import test_r16_connection_close_state as t
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

class DelayCDP(t.FakeCDP):
    def __init__(self, delays=None, **kw):
        super().__init__(**kw)
        self.delays = delays or {}
        self.methods = []
    async def _reader(self, ws, first_connection):
        try:
            async for raw in ws:
                msg = json.loads(raw)
                self.methods.append(msg["method"])
                if msg["method"] in self.drop:
                    continue
                asyncio.ensure_future(self._reply(ws, msg))
        except websockets.exceptions.ConnectionClosed:
            pass
    async def _reply(self, ws, msg):
        await asyncio.sleep(self.delays.get(msg["method"], 0))
        reply = {"id": msg["id"], "result": self.result_for(msg["method"])}
        if "sessionId" in msg:
            reply["sessionId"] = msg["sessionId"]
        try:
            await ws.send(json.dumps(reply))
        except websockets.exceptions.ConnectionClosed:
            pass

def make_tab(peer):
    bc = Connection(peer.url)
    owner = types.SimpleNamespace(connection=bc, config=None)
    tab = Connection(peer.url, target=cdp.target.TargetInfo.from_json(t.TARGET_INFO), _owner=owner)
    return bc, tab

async def tab_aclose_during_attach():
    async with DelayCDP(delays={"Target.attachToTarget": 0.5}) as peer:
        bc, tab = make_tab(peer)
        opener = asyncio.ensure_future(tab.aopen())
        await asyncio.sleep(0.2)
        await asyncio.wait_for(tab.aclose(), 5)
        try:
            await asyncio.wait_for(opener, 5)
        except Exception as e:
            print("  opener raised", type(e).__name__)
        print("tab aclose during attach -> session_id after close:", tab.session_id,
              "| detachFromTarget sent:", "Target.detachFromTarget" in peer.methods)
        await tab.aclose(); await bc.aclose()

async def concurrent_send_and_close():
    # many concurrent senders plus aclose/aopen cycles must never deadlock
    async with DelayCDP(delays={"Target.getTargetInfo": 0.01}, handshake_delay=0.05) as peer:
        conn = Connection(peer.url)
        errors = {}
        async def sender():
            for _ in range(20):
                try:
                    await conn.send(cdp.target.get_target_info())
                except Exception as e:
                    errors[type(e).__name__] = errors.get(type(e).__name__, 0) + 1
        async def closer():
            for _ in range(10):
                await asyncio.sleep(0.03)
                await conn.aclose()
        await asyncio.wait_for(asyncio.gather(*[sender() for _ in range(5)], closer()), 30)
        await conn.aclose()
        await asyncio.sleep(0.3)
        print("concurrent send/aclose: finished, errors:", errors, "| closed:", conn.closed,
              "| server open conns:", peer.open_connections, "| mapper:", len(conn.mapper))

async def aclose_cancelled_while_waiting_for_lock():
    async with DelayCDP(handshake_delay=0.5) as peer:
        conn = Connection(peer.url)
        opener = asyncio.ensure_future(conn.aopen())
        await asyncio.sleep(0.1)
        try:
            await asyncio.wait_for(conn.aclose(), 0.1)
            print("aclose returned before connect finished")
        except asyncio.TimeoutError:
            print("aclose timed out while waiting for the connect (lock held)")
        await asyncio.wait_for(opener, 5)
        print("  after: closed=", conn.closed, "lock locked=", conn._open_lock.locked())
        await asyncio.wait_for(conn.aclose(), 5)
        print("  second aclose ok, closed=", conn.closed)

async def reconnect_after_peer_close_with_tab():
    async with DelayCDP() as peer:
        bc, tab = make_tab(peer)
        await asyncio.wait_for(tab.aopen(), 5)
        peer.flood_session = "S1"
        waiter = asyncio.ensure_future(tab.wait())
        await asyncio.sleep(0.3)
        peer.close_now.set()
        done, _ = await asyncio.wait({waiter}, timeout=3)
        print("peer close with tab: tab.wait() done:", bool(done), "| bc.closed:", bc.closed, "| tab.session_id:", tab.session_id)
        if not done:
            waiter.cancel()
        peer.close_now.clear(); peer.flood_session = False
        try:
            info = await asyncio.wait_for(tab.send(cdp.target.get_target_info()), 5)
            print("  tab re-attached after reconnect:", info.target_id, "session", tab.session_id, "connections", peer.connections)
        except Exception as e:
            print("  tab send after peer close raised", type(e).__name__, e)
        await tab.aclose(); await bc.aclose()

async def main():
    for f in (tab_aclose_during_attach, concurrent_send_and_close,
              aclose_cancelled_while_waiting_for_lock, reconnect_after_peer_close_with_tab):
        try:
            await asyncio.wait_for(f(), 40)
        except Exception as e:
            print(f.__name__, "FAILED", type(e).__name__, e)

async def tab_open_then_close_immediately():
    async with DelayCDP() as peer:
        for _ in range(5):
            bc, tab = make_tab(peer)
            await asyncio.wait_for(tab.aopen(), 5)
            await asyncio.sleep(0)
            await asyncio.wait_for(tab.aclose(), 5)
            await asyncio.sleep(0.05)
            await bc.aclose()

async def tab_open_then_close_sweep():
    async with DelayCDP() as peer:
        for k in range(6):
            for _ in range(2):
                bc, tab = make_tab(peer)
                await tab.aopen()
                for _ in range(k):
                    await asyncio.sleep(0)
                await tab.aclose()
                await asyncio.sleep(0.05)
                await bc.aclose()
