import asyncio, json
import zendriver as zd

async def main():
    async with await zd.start(headless=True) as b:
        pass
    print("after async with: stopped?", b.stopped, "pid", b._process_pid)
    await b.stop()
    try:
        async with await zd.start(headless=True) as b2:
            json.loads("not json")
    except json.JSONDecodeError as e:
        print("caught JSONDecodeError as expected")
    except Exception as e:
        print("instead got", type(e).__name__, str(e)[:100])
    print("b2 stopped?", b2.stopped)
    await b2.stop()
    try:
        async with await zd.start(headless=True) as b3:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(asyncio.sleep(0, result=1/0) if False else _boom())
    except* ZeroDivisionError:
        print("caught ExceptionGroup[ZeroDivisionError] as expected")
    except* Exception as eg:
        print("instead got", [type(x).__name__ for x in eg.exceptions], str(eg.exceptions[0])[:120])
    await b3.stop()

async def _boom():
    1/0

asyncio.run(asyncio.wait_for(main(), 50))
