#!/bin/bash
# gate_posture.sh: field-fight posture decides kill or rout ($5590, strategy.md "Combat").
# Replays runs/l2_scripted_prov (the land-2 scripted run before the posture fix, from scratchpad/cmd3/l2build/l2_built.snap,
# rebuilt by campaign_next.sh) to its 300M snapshot, where side 1's captain (32 men, posture 4) fights side-2 men. Two arms,
# 30M steps each, one variable: a no-poke control and a posture-2 order ($16, y 2) to group 0. Counts $5590 (resolutions),
# $55f2 (kills), $560a (routs) and prints the captain group and side 2's totals. Recorded: control 34 kills, 34 routs,
# captain dissolved; posture 2 49 kills, 4 routs, captain alive with 4 men, side 2 group men 36 against 56.
# Work dir $CMD_WORK/posture (default scratchpad/cmd1).
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=${d#$R/}; W=${CMD_WORK:-scratchpad/cmd1}/posture; rm -rf $W; mkdir -p $W
python3 $L/loop.py $W/replay --replay "$R/$L/runs/l2_scripted_prov/decisions.jsonl" --snap-at 300000000 > $W/replay.json
S=$W/replay/at_300000000.snap
echo '[{"side":1,"type":22,"x":0,"y":2,"group":0}]' > $W/p2.json
python3 $L/step.py $S $W/ctl.snap 30000000 --hits 5590,55f2,560a --quiet &
python3 $L/step.py $S $W/p2.snap 30000000 $W/p2.json --hits 5590,55f2,560a --quiet &
wait
for x in ctl p2; do echo "== $x"; grep -E '^\s+\$0*(5590|55f2|560a) ' $W/$x.out; done
python3 - "$W" <<'EOF'
import sys
sys.path.insert(0, 'reversing/powermonger/commander')
from observe import observe, load
for x in ('ctl', 'p2'):
    o = observe(load(f'{sys.argv[1]}/{x}.snap'))
    cap = [(g['men'], g['state_name'], g['posture']) for g in o['sides'][1]['groups'] if g['alive']]
    t = o['sides'][2]['totals']
    print(x, 'captain', cap or 'dissolved', 'side 2 lords', t['lords'], 'men home', t['men_home'], 'group men', t['group_men'])
EOF
