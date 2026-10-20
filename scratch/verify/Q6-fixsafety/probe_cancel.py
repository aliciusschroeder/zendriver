import asyncio, sys
import zendriver as zd
from zendriver.core.connection import Connection
from zendriver.core.expect import RequestExpectation
print("zendriver from", zd.__file__, sys.version.split()[0])
async def main():
    exp = RequestExpectation(Connection("ws://unused"), r".*")
    await exp._setup()
    try:
        await asyncio.wait_for(exp.value, 0.05)
    except asyncio.TimeoutError:
        pass
    print("request_future cancelled after timed-out wait_for(exp.value):", exp.request_future.cancelled())
asyncio.run(asyncio.wait_for(main(), 10))
