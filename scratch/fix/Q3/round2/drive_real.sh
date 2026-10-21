#!/bin/bash
# drives probe_real.py modes and checks the browser pid and profile after python exits
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-26
HERE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3/round2
PY=${PY:-$WT/.venv/bin/python}
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
cd "$HERE" || exit 1
for mode in "$@"; do
    echo "===== $mode ($PY)"
    out=$(timeout 120 "$PY" -I -W default "$HERE/probe_real.py" "$mode" 2>"$HERE/stderr_$mode.txt")
    echo "$out"
    pid=$(echo "$out" | awk '/^PID/{print $2}')
    udd=$(echo "$out" | awk '/^UDD/{print $2}')
    if [ -n "$pid" ]; then
        if [ -e "/proc/$pid" ]; then
            echo "AFTER EXIT: pid $pid still exists: $(awk '{print $3}' /proc/$pid/stat)"
            kill -CONT "$pid" 2>/dev/null; kill -9 "$pid" 2>/dev/null
        else
            echo "AFTER EXIT: pid $pid gone"
        fi
    fi
    if [ -n "$udd" ]; then
        if [ -e "$udd" ]; then echo "AFTER EXIT: profile exists"; rm -rf "$udd"; else echo "AFTER EXIT: profile removed"; fi
    fi
    echo "--- stderr (filtered):"
    grep -vE "^\s*$" "$HERE/stderr_$mode.txt" | grep -iE "unhandled|error|exception|warning|was never|destroyed" | head -8
done
