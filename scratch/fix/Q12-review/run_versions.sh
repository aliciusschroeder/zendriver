#!/bin/bash
# runs the Q12 regression tests 3 times on the scratch 3.12 and 3.13 venvs
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q12-review
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-24 || exit 1
for v in 312 313; do
  "$S/venv$v/bin/python" -c "import sys, zendriver; print(sys.version.split()[0], zendriver.__file__)"
  for i in 1 2 3; do
    timeout 120 "$S/venv$v/bin/python" -m pytest tests/core/test_connection.py \
      tests/core/test_mouse.py::test_element_mouse_click_does_not_swallow_cancellation \
      -p no:cacheprovider -q "$@" 2>&1 | grep -E "^E  .*(Error|assert)|FAILED|passed|failed" | head -12
  done
done
