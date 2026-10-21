import asyncio, gc, sys, logging
logging.basicConfig(level=logging.INFO)
import zendriver as zd
from zendriver.core.connection import ProtocolException

async def _no_op(*a, **k): return None

async def main():
    print(sys.version.split()[0], zd.__file__)
    tab = zd.Tab.__new__(zd.Tab)
    tab.send = _no_op
    started = asyncio.Event()
    answer = asyncio.get_running_loop().create_future()
    async def wfa(*a, **k):
        started.set()
        return await answer
    tab.query_selector = wfa
    task = asyncio.create_task(tab.select("#x", timeout=5))
    await started.wait()
    answer.set_exception(ProtocolException("boom"))
    task.cancel()
    await asyncio.wait({task}, timeout=5)
    print("cancelled", task.cancelled())
    del task
    gc.collect()
    print("refs to inner tasks:", [t for t in gc.get_objects() if isinstance(t, asyncio.Task)])
    await asyncio.sleep(0.1)
    gc.collect()
    print("end")

asyncio.run(main())
