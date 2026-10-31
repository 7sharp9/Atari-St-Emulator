#!/bin/bash
# Twelve boss-fight start delays, two processes at a time.
#   reversing/impossamole/py/boss/sweep_delays.sh <fight script.py> <tag> [script args]     (D0=<first delay>, default 0)
# Delays D0, D0+100000, ..., D0+1100000 from agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap; one log per delay in
# scratchpad/impossamole/pass108/boss/<tag>/d<delay>.out; prints the RESULT lines (a kill reads `$22803=ff`).
cd "${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}" || exit 1
S=$1; T=$2; shift 2
OUTD=scratchpad/impossamole/pass108/boss/$T
mkdir -p $OUTD
D0=${D0:-0}
for k in 0 2 4 6 8 10; do
  for dl in $((D0 + k*100000)) $((D0 + (k+1)*100000)); do
    ATARI_NOTRACE=1 uv run python $S scratchpad/impossamole/agents/unpoked/hop4s/none/shop/seg5_pit_exit.snap --delay $dl --out p108_${T}_d$dl "$@" > $OUTD/d$dl.out 2>&1 &
  done
  wait
done
grep -H RESULT $OUTD/*.out
