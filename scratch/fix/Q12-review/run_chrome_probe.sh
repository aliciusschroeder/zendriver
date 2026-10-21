#!/bin/bash
# runs chrome_probe.py from the review worktree with the scratch chromium on PATH
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad
export PATH=$S/bin:$PATH
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-24 || exit 1
timeout -k 5 100 .venv/bin/python -u "$S/fix/Q12-review/chrome_probe.py" "$@" > "$S/fix/Q12-review/chrome_out.txt" 2>&1
echo "exit=$?"
tail -30 "$S/fix/Q12-review/chrome_out.txt"
