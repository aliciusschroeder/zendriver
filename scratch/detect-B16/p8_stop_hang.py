import asyncio, os, signal
import zendriver as zd

async def main():
    b = await zd.start(headless=True)
    tab = b.main_tab
    print(await tab.evaluate("1+1"))
    pid = b._process_pid
    os.kill(pid, signal.SIGSTOP)   # browser process stops answering CDP
    task = asyncio.create_task(b.stop())
    await asyncio.sleep(8)
    print("stop done after 8s?", task.done(), "| process terminated?", b._process.poll() if b._process else "reset")
    task.print_stack(limit=30)
    task.cancel()
    os.kill(pid, signal.SIGKILL)
    try:
        await task
    except BaseException as e:
        print("stop task ended with", type(e).__name__)

asyncio.run(asyncio.wait_for(main(), 40))
