#!/bin/bash
# usage: run_new.sh <label> [extra pytest args]
cd /home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5 || exit 1
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
T=(
tests/core/test_connection.py::test_timed_out_domain_enable_that_was_sent_is_not_sent_again
tests/core/test_connection.py::test_rejected_domain_enable_whose_send_timed_out_is_sent_again
tests/core/test_connection.py::test_cancelled_send_leaves_no_command_behind
tests/core/test_connection.py::test_close_during_a_failing_write_leaves_no_unretrieved_failure
tests/core/test_connection.py::test_cancelled_manual_enable_is_enabled_for_handlers_later
tests/core/test_connection.py::test_command_that_failed_while_enabling_domains_is_not_sent
tests/core/test_connection.py::test_receive_error_spares_responses_routed_to_a_session
)
label=$1; shift
echo "== $label 3.10"
timeout 300 uv run pytest "${T[@]}" -p no:cacheprovider -q --tb=line "$@" 2>&1 | grep -v UV_NATIVE | tail -15
echo "== $label 3.13"
UV_PROJECT_ENVIRONMENT=$S/venv313 timeout 300 uv run pytest "${T[@]}" -p no:cacheprovider -q --tb=line "$@" 2>&1 | grep -v UV_NATIVE | tail -15
