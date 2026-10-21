#!/bin/bash
# usage: drive.sh PYTHON MODE ; runs the probe from the worktree and checks pid/profile after exit
PY="$1"
MODE="$2"
HERE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3-review2
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-28 || exit 1
T0=$(date +%s.%N)
OUT=$(timeout 120 "$PY" "$HERE/probe.py" "$MODE" 2>"$HERE/stderr_${MODE}_$(basename $(dirname $(dirname $PY))).txt")
RC=$?
T1=$(date +%s.%N)
echo "$OUT"
echo "rc=$RC total=$(echo "$T1 - $T0" | bc)"
PID=$(echo "$OUT" | awk '/^PID/{print $2}')
UDD=$(echo "$OUT" | awk '/^UDD/{print $2}')
if [ -n "$PID" ]; then
  if [ -e /proc/$PID ]; then
    echo "AFTER EXIT: pid $PID exists state=$(awk '{print $3}' /proc/$PID/stat)"
    kill -CONT "$PID" 2>/dev/null; kill -9 "$PID" 2>/dev/null
  else
    echo "AFTER EXIT: pid $PID gone"
  fi
fi
if [ -n "$UDD" ]; then
  if [ -e "$UDD" ]; then echo "AFTER EXIT: profile exists"; rm -rf "$UDD"; else echo "AFTER EXIT: profile removed"; fi
fi
grep -E "never retrieved|Unhandled exception|Traceback|Error" "$HERE/stderr_${MODE}_$(basename $(dirname $(dirname $PY))).txt" | head -5
