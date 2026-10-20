import subprocess, signal, os, sys, time, shutil
D = os.path.dirname(os.path.abspath(__file__))
env = dict(os.environ, PATH="/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:" + os.environ["PATH"])
def run(group):
    p = subprocess.Popen(["/home/user/zendriver/.venv/bin/python", "p_ctrlc2.py"], cwd=D, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                         preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))
    line = p.stdout.readline().decode().split()
    cpid, udd = int(line[0]), line[1]
    time.sleep(3)
    if group: os.killpg(p.pid, signal.SIGINT)
    else: os.kill(p.pid, signal.SIGINT)
    try:
        _, err = p.communicate(timeout=20)
        res = "python exited rc=%s" % p.returncode
    except subprocess.TimeoutExpired:
        os.kill(p.pid, signal.SIGUSR1); time.sleep(1); p.kill(); _, err = p.communicate()
        res = "python HUNG >20s"
    time.sleep(0.5)
    try:
        st = open(f"/proc/{cpid}/stat").read().split()[2]
    except FileNotFoundError:
        st = "gone"
    print("group" if group else "python-only", "|", res, "| chrome:", st, "| profile exists:", os.path.exists(udd))
    print("   stderr:", " ".join(l[:200] for l in err.decode().splitlines() if l.strip())[:1500])
    try: os.kill(cpid, signal.SIGKILL)
    except ProcessLookupError: pass
    shutil.rmtree(udd, ignore_errors=True)
for g in (True, False, True):
    run(g)
