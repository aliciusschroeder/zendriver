#!/bin/bash
# runs test_connection.py under -X dev with asyncio debug on both Pythons, showing warnings
cd /home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5 || exit 1
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
export PYTHONASYNCIODEBUG=1
echo "== 3.10"
timeout 300 .venv/bin/python -X dev -m pytest tests/core/test_connection.py -p no:cacheprovider -q -rw -o log_cli=false 2>&1 | grep -iE "passed|failed|never retrieved|destroyed|never awaited|Warning" | sort | uniq -c | head -20
echo "== 3.13"
timeout 300 "$S/venv313/bin/python" -X dev -m pytest tests/core/test_connection.py -p no:cacheprovider -q -rw 2>&1 | grep -iE "passed|failed|never retrieved|destroyed|never awaited|Warning" | sort | uniq -c | head -20
