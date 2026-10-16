#!/bin/bash
# gate_move.sh: A* leg orders against direct orders (ab.py, 9 pairs, BUDGET 120M) from rand1 and two boat-stripped
# starts built by prep.py, then a --move loop run twice on side 1 (identical log and snapshot). Work dir $CMD_WORK/move.
set -e
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=${d#$R/}; W=${CMD_WORK:-scratchpad/cmd1}/move; mkdir -p $W
[ -f $W/prep1.snap ] || python3 $L/prep.py scratchpad/pm142/rand1.snap $W/prep1.snap 20e6 2:0 3:0 3:1 4:0 > $W/prep1.txt
[ -f $W/prep2.snap ] || python3 $L/prep.py scratchpad/pm143/run/rand1_s2.snap $W/prep2.snap 20e6 3:0 2:0 4:2 > $W/prep2.txt
BUDGET=${BUDGET:-120e6} python3 $L/ab.py
B=${2:-400e6}
python3 $L/loop.py $W/det_a --side 1 --move --budget $B > /dev/null &
python3 $L/loop.py $W/det_b --side 1 --move --budget $B > /dev/null &
wait
cmp $W/det_a/final.snap $W/det_b/final.snap && echo "final.snap det_a == det_b"
diff $W/det_a/decisions.jsonl $W/det_b/decisions.jsonl && echo "log det_a == det_b"
