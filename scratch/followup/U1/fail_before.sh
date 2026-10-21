#!/bin/bash
# runs the new tests against the base zendriver/ (fail before) and HEAD (pass after)
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-1
V313=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1/venv313
cd "$W"
TESTS=(
  "tests/core/test_connection.py::test_timed_out_domain_enable_that_was_sent_is_not_sent_again"
  "tests/core/test_connection.py::test_rejected_domain_enable_whose_send_timed_out_is_sent_again"
  "tests/core/test_connection.py::test_cancelled_send_leaves_no_command_behind"
  "tests/core/test_connection.py::test_close_during_a_failing_write_leaves_no_unretrieved_failure"
  "tests/core/test_connection.py::test_cancelled_manual_enable_is_enabled_for_handlers_later"
  "tests/core/test_connection.py::test_command_that_failed_while_enabling_domains_is_not_sent"
  "tests/core/test_connection.py::test_receive_error_spares_responses_routed_to_a_session"
)
run() {
  echo "### 3.10 ($1)"
  timeout 300 uv run pytest "${TESTS[@]}" -p no:cacheprovider -q -rA 2>&1 | grep -E "^(PASSED|FAILED|ERROR)|^E  |passed|failed" | head -60
  echo "### 3.13 ($1)"
  UV_PROJECT_ENVIRONMENT=$V313 timeout 300 uv run pytest "${TESTS[@]}" -p no:cacheprovider -q -rA 2>&1 | grep -E "^(PASSED|FAILED|ERROR)|^E  |passed|failed" | head -60
}
git checkout ccr-9a8a26e1-b0l7bh -- zendriver/
git status --short
run base
git checkout HEAD -- zendriver/
git status --short
run fix
