import asyncio, gc, sys, logging, traceback
logging.basicConfig(level=logging.INFO)
import zendriver as zd
from zendriver.core.connection import ProtocolException

class T(asyncio.tasks._PyTask):
    def exception(self):
        traceback.print_stack(limit=6)
        return super().exception()
    def result(self):
        traceback.print_stack(limit=6)
        return super().result()

async def _no_op(*a, **k): return None

async def main():
    asyncio.get_running_loop().set_task_factory(lambda loop, coro: T(coro, loop=loop))
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

asyncio.run(main())
