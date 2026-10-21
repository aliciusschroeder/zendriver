#!/usr/bin/env bash
# Merge one fix branch into the designated branch, then run lint and the full headless suite.
# usage: integrate_one.sh <fix-branch>     (stops on conflict; prints a summary line)
set -u
REPO=/home/user/zendriver
SCR=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad
LOG=$SCR/integration
mkdir -p "$LOG"
b="$1"; slug="${b#fix/}"
cd "$REPO" || exit 2
[ "$(git rev-parse --abbrev-ref HEAD)" = "ccr-9a8a26e1-b0l7bh" ] || { echo "not on designated branch"; exit 2; }
subject=$(git log -1 --format=%s "$b")
if ! git merge --no-ff -q -m "Merge $b: $subject" "$b" > "$LOG/$slug.merge.txt" 2>&1; then
  echo "CONFLICT merging $b:"; git diff --name-only --diff-filter=U; exit 3
fi
bash scripts/lint.sh > "$LOG/$slug.lint.txt" 2>&1; lint=$?
export PATH=$SCR/bin:$PATH
ZENDRIVER_TEST_BROWSERS=headless timeout 900 uv run pytest -n 4 -p no:cacheprovider -q -rfs > "$LOG/$slug.tests.txt" 2>&1; tests=$?
grep "^FAILED" "$LOG/$slug.tests.txt"
echo "$b merged as $(git rev-parse --short HEAD): lint=$lint tests=$tests :: $(tail -1 "$LOG/$slug.tests.txt")"
