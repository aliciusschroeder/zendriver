import asyncio, time, os, signal
import zendriver as zd

async def main():
    browser = await zd.start(headless=True)
    tab = await browser.get("data:text/html,<p>hi</p>")
    await tab.evaluate("1")  # attach the tab's flat session
    pid = browser._process_pid
    os.kill(pid, signal.SIGSTOP)  # browser process stops answering CDP
    t0 = time.monotonic()
    task = asyncio.ensure_future(browser.stop())
    done, _ = await asyncio.wait({task}, timeout=20)
    if task in done:
        print(f"stop() returned after {time.monotonic()-t0:.1f}s, exc={task.exception()!r}")
    else:
        print(f"stop() STILL PENDING after {time.monotonic()-t0:.1f}s; process alive: {browser._process.poll() is None}")
        task.print_stack(limit=20)
        task.cancel()
    os.kill(pid, signal.SIGKILL)

asyncio.run(main())
