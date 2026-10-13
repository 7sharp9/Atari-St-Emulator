#!/bin/bash
# gate_loop.sh [BUDGET]: the decision loop on side 3 (default 1G steps): two scripted runs, a replay of the first, a --read snap run, and two controls, in parallel.
# Run from anywhere; finds M68000 by walking up to tools/rdis.py.
set -e
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=${d#$R/}; B=${1:-1e9}; W=${CMD_WORK:-scratchpad/cmd1}/loop
mkdir -p $W
python3 $L/loop.py $W/run1 --budget $B > $W/run1.json &
python3 $L/loop.py $W/run2 --budget $B > $W/run2.json &
python3 $L/loop.py $W/run3snap --budget $B --read snap > $W/run3snap.json &
python3 $L/loop.py $W/ctl_take --budget $B --policy none > $W/ctl_take.json &
python3 $L/loop.py $W/ctl_none --budget $B --policy none --no-take > $W/ctl_none.json &
wait
python3 $L/loop.py $W/replay --replay $W/run1/decisions.jsonl > $W/replay.json
for r in run2 run3snap replay; do
  cmp $W/run1/final.snap $W/$r/final.snap && echo "final.snap run1 == $r"
done
diff $W/run1/decisions.jsonl $W/run2/decisions.jsonl && echo "log run1 == run2"
diff $W/run1/decisions.jsonl $W/run3snap/decisions.jsonl && echo "log run1 == run3snap"
diff <(grep -v '"start"' $W/run1/decisions.jsonl | sed 's/"actions":\[[^]]*\],*//') \
     <(grep -v '"start"' $W/replay/decisions.jsonl | sed 's/"actions":\[[^]]*\],*//') && echo "log run1 == replay (bar start/actions)"
