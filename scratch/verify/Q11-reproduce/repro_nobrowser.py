import asyncio, sys, time
import zendriver
from zendriver.core.tab import Tab
print("zendriver from:", zendriver.__file__, "python", sys.version.split()[0])

async def main():
    tab = Tab.__new__(Tab)  # bypass __init__, no browser needed
    calls = []
    async def fake_evaluate(expr, *a, **k):
        calls.append(expr)
        return "complete"
    tab.evaluate = fake_evaluate  # instance patch
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(tab.wait_for_ready_state(timeout=2), 10)
        print("returned", r, f"{time.monotonic()-t0:.2f}s")
    except asyncio.TimeoutError as e:
        print(f"TimeoutError after {time.monotonic()-t0:.2f}s, evaluate polled {len(calls)} times: {e}")

asyncio.run(main())
