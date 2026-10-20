#!/bin/bash
D=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/Q3-refute
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
cd $D
rm -f out3.txt err3.txt
setsid /home/user/zendriver/.venv/bin/python p_ctrlc2.py > out3.txt 2> err3.txt < /dev/null &
PY=$!
sleep 7
read cpid udd < out3.txt
kill -INT -- -$PY
sleep 3
echo "chrome state after 3s: $(awk '{print $3}' /proc/$cpid/stat 2>/dev/null || echo gone)"
kill -USR1 $PY 2>/dev/null
sleep 1
for i in $(seq 1 30); do kill -0 $PY 2>/dev/null || break; sleep 0.5; done
kill -0 $PY 2>/dev/null && echo "python still running after ~19s" 
kill -9 $PY 2>/dev/null
echo "----- stderr:"; cut -c1-220 err3.txt | grep -v "^\s*$" | head -40
[ -e /proc/$cpid ] && echo "chrome alive" || echo "chrome gone"
[ -d "$udd" ] && echo "profile LEAKED" || echo "profile removed"
kill -9 $cpid 2>/dev/null; sleep 0.5; rm -rf "$udd"
