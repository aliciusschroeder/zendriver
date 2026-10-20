import asyncio, os, sys, time, psutil
import zendriver, faulthandler
faulthandler.dump_traceback_later(95, exit=False)
print("zendriver from", zendriver.__file__, sys.version.split()[0], flush=True)
async def main():
    b = await zendriver.start(headless=True, browser_args=["--enable-logging=stderr"])
    proc = b._process; pid = proc.pid
    print("udd", b.config.user_data_dir, flush=True)
    tab = b.main_tab
    for i in range(40):
        try:
            await asyncio.wait_for(tab.evaluate("for (let k=0;k<20;k++) console.log('y'.repeat(200)); 1"), 10)
        except asyncio.TimeoutError:
            print("hung at round", i, flush=True); break
    ts = time.monotonic()
    st = asyncio.ensure_future(b.stop())
    done, _ = await asyncio.wait({st}, timeout=20)
    if done:
        print("stop returned in %.1fs exc=%r" % (time.monotonic()-ts, st.exception()), flush=True)
    else:
        print("stop still pending after 40s; stack:", flush=True)
        st.print_stack()
        print('killing', flush=True)
        for c in psutil.Process(pid).children(recursive=True):
            c.kill()
        print('children killed', flush=True)
        proc.kill(); print('killed main', flush=True); proc.wait(); print('reaped', flush=True)
        try:
            await asyncio.wait_for(st, 15)
            print("stop finished after kill", flush=True)
        except Exception as e:
            print("stop after kill:", repr(e), flush=True)
    print("udd exists after:", os.path.exists(b.config.user_data_dir), flush=True)
asyncio.run(main())
