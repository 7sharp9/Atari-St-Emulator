#!/bin/bash
# gate_rollout.sh: determinism of forking. A rollout of candidate c from a decision snapshot ends byte-identical (cmp) to the
# loop's own continuation when the loop issued c there and ran the same steps.
#  (a) decision 0 on rand1, side 3, N=20M: one rl_loop run per candidate, each forced to issue that candidate
#      (--force), budget 20M: the run's final.snap against its own ro/0/<c>.snap.
#  (b) one 300M run, a decision every 20M and N=20M, --snap-at every 20M: every rollout decision's chosen candidate's
#      snapshot against the loop's at_<D+N>.snap (no other poke falls in (D, D+N] since the next decision is at D+N).
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=${d#$R/}; W=${CMD_WORK:-scratchpad/cmd1}/rollout; mkdir -p $W
N=20e6
ok=0; bad=0
for c in scripted none get_food attack_loose attack_2nd; do
  rm -rf $W/f_$c
  python3 $L/loop.py $W/f_$c --policy rollout --budget $N --every 1e9 --N $N --K 5 --force $c > $W/f_$c.json
  if cmp $W/f_$c/final.snap $W/f_$c/ro/0/$c.snap; then echo "(a) $c: loop final.snap == rollout $c.snap"; ok=$((ok+1)); else bad=$((bad+1)); fi
done
rm -rf $W/mid
SA=$(python3 -c "print(','.join(str(20_000_000*i) for i in range(1,16)))")
python3 $L/loop.py $W/mid --policy rollout --budget 300e6 --every $N --N $N --K 5 --snap-at $SA > $W/mid.json
for D in $(python3 -c "
import json
for l in open('$W/mid/decisions.jsonl'):
    r=json.loads(l)
    if r['kind']=='decision' and 'rollout' in r: print(r['step'], r['rollout']['best'])
" | tr ' ' ':'); do
  s=${D%%:*}; b=${D#*:}; e=$((s+20000000))
  if cmp $W/mid/ro/$s/$b.snap $W/mid/at_$e.snap; then echo "(b) D=$s best=$b: rollout == loop at $e"; ok=$((ok+1)); else bad=$((bad+1)); fi
done
echo "gate_rollout: $ok equal, $bad differ"
