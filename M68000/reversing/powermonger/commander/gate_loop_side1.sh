#!/bin/bash
# gate_loop_side1.sh [BUDGET]: the scripted baseline on the local side 1, twice, to a land end or the budget, and a
# replay of the first run. Work dir $CMD_WORK/loop_side1 (default scratchpad/cmd1).
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=${d#$R/}; B=${1:-2e9}; W=${CMD_WORK:-scratchpad/cmd1}/loop_side1
mkdir -p $W
python3 $L/loop.py $W/s1a --side 1 --budget $B > $W/s1a.json &
python3 $L/loop.py $W/s1b --side 1 --budget $B > $W/s1b.json &
wait
cmp $W/s1a/final.snap $W/s1b/final.snap && echo "final.snap s1a == s1b"
diff $W/s1a/decisions.jsonl $W/s1b/decisions.jsonl && echo "log s1a == s1b"
python3 $L/loop.py $W/replay --replay $W/s1a/decisions.jsonl > $W/replay.json
cmp $W/s1a/final.snap $W/replay/final.snap && echo "final.snap s1a == replay"
grep '"end"' $W/s1a/decisions.jsonl | cut -c1-300
