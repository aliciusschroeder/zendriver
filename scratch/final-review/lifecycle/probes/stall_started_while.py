"""test_browser_stop_keeps_a_process_started_while_it_ran with a 0.15 s event loop stall
(as on a loaded runner) right after stop() is scheduled."""
import asyncio, sys, time, shutil, subprocess
import zendriver as zd
from tests.core.test_browser import EXITS_A_WHILE_AFTER_SIGTERM, EXITS_ON_SIGTERM

def make(program):
    browser = zd.Browser(zd.Config(browser_executable_path=sys.executable))
    p = subprocess.Popen([sys.executable, "-c", program], stdout=subprocess.PIPE)
    assert p.stdout.readline().strip() == b"ready"
    browser._process, browser._process_pid = p, p.pid
    return browser, p

async def main(stall):
    browser, process = make(EXITS_A_WHILE_AFTER_SIGTERM)
    _, new_process = make(EXITS_ON_SIGTERM)
    stop = asyncio.create_task(browser.stop())
    if stall:
        asyncio.get_running_loop().call_soon(time.sleep, 0.15)
    await asyncio.sleep(0.1)
    browser._process, browser._process_pid = new_process, new_process.pid
    await asyncio.wait_for(stop, timeout=10)
    ok = process.poll() is not None and browser._process is new_process
    print(f"stall={stall}: old exited={process.poll() is not None} new rc={new_process.poll()} kept_new={browser._process is new_process} -> {'PASS' if ok else 'FAIL'}")
    for p in (process, new_process):
        if p.poll() is None: p.kill()
        p.wait()
    shutil.rmtree(browser.config.user_data_dir, ignore_errors=True)
    shutil.rmtree(_.config.user_data_dir, ignore_errors=True)

print(sys.version.split()[0], zd.__file__)
asyncio.run(main(False)); asyncio.run(main(True))
