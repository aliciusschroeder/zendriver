#!/bin/bash
# real chromium: SIGSTOP + wait_for(stop(), 3) with the round-1 gather (mutation) and then the fix
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-26
HERE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3/round2
cd "$WT" || exit 1
cp zendriver/core/browser.py "$HERE/browser.py.fixed"
uv run python "$HERE/mutate.py" "$WT" gather_to_wait_for 2>&1 | grep applied
bash "$HERE/drive_real.sh" sigstop_waitfor > /dev/null 2>&1
echo "round-1 gather: never retrieved lines: $(grep -c 'never retrieved' "$HERE/stderr_sigstop_waitfor.txt")"
grep -m1 "never retrieved" "$HERE/stderr_sigstop_waitfor.txt"
cp "$HERE/stderr_sigstop_waitfor.txt" "$HERE/stderr_sigstop_waitfor_round1.txt"
cp "$HERE/browser.py.fixed" zendriver/core/browser.py
cmp "$HERE/browser.py.fixed" zendriver/core/browser.py && echo restored
bash "$HERE/drive_real.sh" sigstop_waitfor | grep -E "timed out|AFTER EXIT|returned"
echo "fix: never retrieved lines: $(grep -c 'never retrieved' "$HERE/stderr_sigstop_waitfor.txt")"
