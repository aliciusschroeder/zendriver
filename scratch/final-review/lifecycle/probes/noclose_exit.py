"""run_until_complete without closing the loop (no atexit), interpreter exits with chrome
running and the drain thread blocked in os.read. exit must be prompt."""
import asyncio, shutil, sys, time
import zendriver as zd
CHROME = shutil.which("chromium")
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
async def main():
    b = await zd.start(headless=True, sandbox=False, browser_executable_path=CHROME,
                       browser_args=["--enable-logging=stderr", "--v=1"])
    await b.get("data:text/html,<p>x</p>")
    print("PID", b._process_pid, flush=True)
    print("UDD", b.config.user_data_dir, flush=True)
loop.run_until_complete(main())
print("T", time.time(), flush=True)
