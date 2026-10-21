#!/bin/bash
# runs the reviewer probes against the worktree checkout on 3.10, 3.11, 3.13
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
WT=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-4
D=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/cancellation
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad
PYS="$WT/.venv/bin/python $S/fix/Q3-review2/venv3.11/bin/python $S/followup/U2-review1/venv313/bin/python"
PROBES="${@:-$D/probe_cancel_swallow.py $D/probe_cancel_swallow_loop.py $D/probe_inf_timeout.py}"
for py in $PYS; do
  for p in $PROBES; do
    echo "== $($py -c 'import sys; print(sys.version.split()[0])') $(basename $p)"
    PYTHONPATH=$WT timeout 60 $py $p 2>&1 | tail -${TAIL:-6}
  done
done
