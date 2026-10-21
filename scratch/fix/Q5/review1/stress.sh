#!/bin/bash
# run the new tests repeatedly while 8 busy loops load the 4 cpus
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-18 || exit 1
PY=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-18/.venv/bin/python
pids=()
for _ in 1 2 3 4 5 6 7 8; do
  "$PY" -c "while True: pass" &
  pids+=($!)
done
for i in $(seq 1 "${1:-10}"); do
  "$PY" -m pytest tests/core/test_util.py -p no:cacheprovider -q -n 4 2>&1 | tail -1
done
kill "${pids[@]}"
