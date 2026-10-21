#!/bin/bash
# sigint_drive.sh <python> <mode> [delay]
P=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/lifecycle/probes
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
before=$(ls -d /tmp/uc_* 2>/dev/null | sort)
out=$(timeout 60 $1 $P/sigint_real.py $2 $3 2>&1); rc=$?
pid=$(echo "$out" | awk '/^PID/{print $2}')
sleep 0.5
after=$(ls -d /tmp/uc_* 2>/dev/null | sort)
udd=$(echo "$out" | awk '/^UDD/{print $2}'); left=no; [ -n "$udd" ] && [ -e "$udd" ] && left=yes
alive=no; [ -n "$pid" ] && kill -0 $pid 2>/dev/null && alive=yes
echo "mode=$2 $3 rc=$rc chrome_alive=$alive profile_left=$left :: $(echo "$out" | grep -v '^PID\|^PROFILE\|^UDD' | tr '\n' '|' | cut -c1-400)"
[ "$alive" = yes ] && kill -9 $pid
