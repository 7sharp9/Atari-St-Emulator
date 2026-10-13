#!/bin/bash
# gate_win.sh [snap] [policy args...]: the commander plays the local side 1 to a won land. Default: campaign land 0
# (pm123/win/m1_s0.snap, 26 men against 20, ratio 2) with the scripted baseline, twice; both runs must end at $d2c8 with
# ratio 4, identical logs and final snapshots, and the victory routine $1a4da (not the defeat $1a5b2) must run next.
# Work dir $CMD_WORK/win (default scratchpad/cmd1).
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; L=${d#$R/}; W=${CMD_WORK:-scratchpad/cmd1}/win; mkdir -p $W
S=${1:-scratchpad/pm123/win/m1_s0.snap}; shift 2>/dev/null
for r in a b; do python3 $L/loop.py $W/$r --snap $S --side 1 --budget 1e9 "$@" > $W/$r.json & done; wait
cmp $W/a/final.snap $W/b/final.snap && echo "final.snap a == b"
diff $W/a/decisions.jsonl $W/b/decisions.jsonl > /dev/null && echo "log a == b"
tail -1 $W/a/decisions.jsonl | python3 -c "import json,sys; e=json.load(sys.stdin); print('end', e['reason'], e['step'], 'ratio', e['ratio'])"
printf 'disk scratchpad/powermonger.st\nhits 3000000 1a4da 1a5b2\nq\n' | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll \
  resume $W/a/final.snap repl 2>/dev/null | grep -E '\$0*(1a4da|1a5b2) '
