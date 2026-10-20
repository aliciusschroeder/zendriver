import asyncio, os, sys, time, signal
import zendriver
def threads(pid):
    out=[]
    try:
        for tid in sorted(os.listdir(f"/proc/{pid}/task")):
            try:
                st=open(f"/proc/{pid}/task/{tid}/stat").read().rsplit(')',1)[1].split()[0]
                w=open(f"/proc/{pid}/task/{tid}/wchan").read()
                comm=open(f"/proc/{pid}/task/{tid}/comm").read().strip()
                out.append((tid,comm,st,w))
            except OSError: pass
    except OSError as e:
        return repr(e)
    return out
async def main():
    b = await zendriver.start(headless=True, browser_args=["--enable-logging=stderr"])
    proc=b._process; pid=proc.pid
    print("udd", b.config.user_data_dir, flush=True)
    for i in range(40):
        try:
            await asyncio.wait_for(b.main_tab.evaluate("for (let k=0;k<20;k++) console.log('y'.repeat(200)); 1"), 10)
        except asyncio.TimeoutError:
            print("hung at round", i, flush=True); break
    print("main status line:", open(f"/proc/{pid}/stat").read().rsplit(')',1)[1].split()[0], flush=True)
    os.kill(pid, signal.SIGKILL)
    for k in range(10):
        time.sleep(0.5)
        r = os.waitpid(pid, os.WNOHANG)
        t = threads(pid)
        nonD = [x for x in t if isinstance(t, list) and x[2] != 'Z'] if isinstance(t, list) else t
        print(k, "waitpid", r, "nonzombie threads:", nonD[:8], flush=True)
        if r[0] == pid:
            proc.returncode = -9
            break
    # finish
    os.read(proc.stderr.fileno(), 1<<20) if False else None
    try:
        await asyncio.wait_for(b.stop(), 20)
        print("stop ok", flush=True)
    except Exception as e:
        print("stop:", repr(e), flush=True)
    print("udd exists:", os.path.exists(b.config.user_data_dir))
asyncio.run(main())
