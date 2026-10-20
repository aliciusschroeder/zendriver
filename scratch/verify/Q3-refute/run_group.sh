#!/bin/bash
# run probe in its own session/process group, then SIGINT the whole group (what a terminal Ctrl+C does)
D=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/Q3-refute
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
cd $D
rm -f out2.txt err2.txt
setsid /home/user/zendriver/.venv/bin/python p_ctrlc.py > out2.txt 2> err2.txt < /dev/null &
PY=$!
sleep 7
read cpid udd < out2.txt
PGID=$(ps -o pgid= -p $PY | tr -d ' ')
echo "py=$PY pgid=$PGID chrome=$cpid chrome_pgid=$(ps -o pgid= -p $cpid | tr -d ' ')"
kill -INT -- -$PGID
for i in $(seq 1 20); do kill -0 $PY 2>/dev/null || break; sleep 0.5; done
kill -9 $PY 2>/dev/null
echo "stderr: $(cut -c1-160 err2.txt | tr '\n' ' ')"
[ -e /proc/$cpid ] && echo "chrome alive" || echo "chrome gone"
[ -d "$udd" ] && echo "profile LEAKED" || echo "profile removed"
kill -9 $cpid 2>/dev/null; rm -rf "$udd"
