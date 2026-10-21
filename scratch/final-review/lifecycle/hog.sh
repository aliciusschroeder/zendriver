#!/bin/bash
# N busy loops for D seconds
N=${1:-4}; D=${2:-300}
for i in $(seq $N); do timeout $D bash -c 'while :; do :; done' & done
wait
