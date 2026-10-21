"""new body of test_browser_stop_keeps_a_process_started_while_it_ran with event loop
stalls injected at several points: right after stop() is scheduled, and right after
the 'terminating' line was read (before the swap)."""
import sys

sys.path.insert(0, "/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-6")
import asyncio, shutil, subprocess, time

import zendriver as zd
from tests.core.test_browser import EXITS_A_WHILE_AFTER_SIGTERM, EXITS_ON_SIGTERM


def make(program):
    browser = zd.Browser(zd.Config(browser_executable_path=sys.executable))
    p = subprocess.Popen([sys.executable, "-c", program], stdout=subprocess.PIPE)
    assert p.stdout.readline().strip() == b"ready"
    browser._process, browser._process_pid = p, p.pid
    return browser, p


async def main(where, stall):
    browser, process = make(EXITS_A_WHILE_AFTER_SIGTERM)
    other, new_process = make(EXITS_ON_SIGTERM)
    loop = asyncio.get_running_loop()
    stop = asyncio.create_task(browser.stop())
    if where == "after_create":
        loop.call_soon(time.sleep, stall)
    line = await asyncio.wait_for(asyncio.to_thread(process.stdout.readline), 10)
    assert line.strip() == b"terminating", line
    if where == "before_swap":
        time.sleep(stall)
    browser._process, browser._process_pid = new_process, new_process.pid
    await asyncio.wait_for(stop, timeout=10)
    ok = (
        process.poll() is not None
        and browser._process is new_process
        and browser._process_pid == new_process.pid
    )
    print(
        f"{where} stall={stall}: old exited={process.poll() is not None} "
        f"new rc={new_process.poll()} kept_new={browser._process is new_process} "
        f"-> {'PASS' if ok else 'FAIL'}"
    )
    for p in (process, new_process):
        if p.poll() is None:
            p.kill()
        p.wait()
    shutil.rmtree(browser.config.user_data_dir, ignore_errors=True)
    shutil.rmtree(other.config.user_data_dir, ignore_errors=True)


print(sys.version.split()[0], zd.__file__)
for where in ("after_create", "before_swap"):
    for stall in (0, 0.15, 0.3, 0.6, 1.0):
        asyncio.run(main(where, stall))
