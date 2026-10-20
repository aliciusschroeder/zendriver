"""Shows why the receive-error handler must not simply `continue`: a persistent
error raised before the first suspension (like websockets' ConcurrencyError)
then spins without yielding and freezes the event loop (Python >= 3.12)."""
import asyncio, json, logging, sys, threading, time
import websockets
from websockets.exceptions import ConcurrencyError
import zendriver
from zendriver.core.connection import Connection
logging.getLogger("uc.connection").setLevel(logging.CRITICAL)
print("python", sys.version.split()[0], "zendriver:", zendriver.__file__)

class AlwaysBusyWS:
    closed = False
    async def send(self, m): pass
    async def recv(self):
        raise ConcurrencyError("cannot call recv while another coroutine is already running recv")
    async def close(self): self.closed = True

async def main():
    async def connect(*a, **k): return AlwaysBusyWS()
    websockets.connect = connect
    ticks = 0
    async def heartbeat():
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.01)
    hb = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.05)
    before = ticks
    conn = Connection("ws://fake/devtools/browser/x")
    # watchdog thread: if the loop is frozen, report and hard-exit
    def watchdog():
        time.sleep(3)
        print(f"FROZEN: event loop made no progress for 3s (heartbeat ticks {ticks - before})", flush=True)
        import os; os._exit(3)
    threading.Thread(target=watchdog, daemon=True).start()
    await conn.aopen()
    await asyncio.sleep(0.5)
    print(f"loop alive: heartbeat ticked {ticks - before} times in ~0.5s; listener running={conn.listener.running}", flush=True)
    import os; os._exit(0)

asyncio.run(main())
