#!/bin/bash
# usage: diag_seeds.sh <fix|base> <310|313> <first> <last>
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
for seed in $(seq "$3" "$4"); do
  bash "$S/diag_loop.sh" "$1" "$2" "$seed" 1
done
