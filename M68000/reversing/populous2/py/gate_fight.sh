#!/bin/bash
# Gate fight_238dc: the fight round (entity state $e) and the whole fight on the first natural fight of conquest
# battles 445 and 775. Builds each battle's start by the title poke (god/battle_census.sh, 1-step census), stops at
# the first state-$e round's rand call ($2391e), then fight_gate.py: per-round model under 16 seeds and poked
# strengths (control: the random multiplier the dead D2 suggests), and the whole fight to the resolution $247e2.
# Run from anywhere:  bash reversing/populous2/py/gate_fight.sh [outdir]
set -e
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; cd "$d"
OUT=${1:-scratchpad/populous2/fight_gate}
mkdir -p "$OUT"
bash reversing/populous2/py/god/battle_census.sh "$OUT" 1 445 775 > "$OUT/census.out" 2>&1
for n in 445 775; do
  rm -f "$OUT/fight$n.snap"
  printf "bp 2391e 30000000\nsnap $OUT/fight$n.snap\nq\n" |
    ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$OUT/b${n}_start.snap" repl > "$OUT/fight$n.log" 2>&1
  echo "battle $n:"
  uv run python reversing/populous2/py/fight_gate.py "$OUT/fight$n.snap" 16
done
