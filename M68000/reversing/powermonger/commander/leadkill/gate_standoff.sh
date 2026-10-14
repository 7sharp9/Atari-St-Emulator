#!/bin/bash
# gate_standoff.sh [arm/o<k> ...]: how the captain's lead dies across the land-2 seeds (README "How the captain dies").
# Each cmd9 run (seeds.sh: scripted, evade, rollout, avoid, diseng x o0..o5) is replayed from its log with
# loop.py --objs 1e5 into ${CMD_WORK:-scratchpad/cmd11}/so/<arm>/o<k>; standoff.py reads the samples. A replay must end
# at the logged step with the logged obs_hash (the sampling must not perturb the run): recorded 30/30.
# Recorded: 23 leads killed in melee, 1 by two arrows (rollout/o5 at 344.1M, $5b4c in $596a: 95 -> 13 -> dead),
# 6 alive (rollout/o0 the win, evade/o0 and rollout/o3 at the 2G budget, scripted/o0 = diseng/o0 and evade/o3 by the
# no-lord retire); the trade bound holds in all 39 sequences; every killing sequence fought 120 to 553 health,
# every survived one at most 150; the men fought in a killing sequence picked the lead from 0 to 4081 units away.
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=${d#$R/}; C=$(dirname $L); W=${CMD_WORK:-scratchpad/cmd11}/so
RUNS="$*"; [ -n "$RUNS" ] || RUNS=$(cd scratchpad/cmd9 && ls -d scripted/o* evade/o* rollout/o* avoid/o* diseng/o*)
for r in $RUNS; do
  [ -f $W/$r/final.snap ] || echo "$C/loop.py $W/$r --replay scratchpad/cmd9/$r/decisions.jsonl --objs 1e5"
done | xargs -P ${PAR:-7} -I{} sh -c 'python3 {} > /dev/null 2>&1'
same=0
for r in $RUNS; do
  e() { tail -1 $1 | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['step'], r.get('obs_hash'))"; }
  [ "$(e scratchpad/cmd9/$r/decisions.jsonl)" = "$(e $W/$r/decisions.jsonl)" ] && same=$((same+1)) || echo "DIFF $r"
  python3 $L/standoff.py $W/$r scratchpad/cmd9/start/${r#*/}/final.snap
done
echo "replays identical to their logs: $same"
