#!/bin/bash
# Gate people_battles: place_people $22986 unpoked on later conquest battles. For each battle, gen_entry.sh builds its
# gen_land-entry snapshot by the title poke of $473a0, then people_gate.py --natural callcaps $22986 against the model.
# Battles: 290 (side 2 leader, pass 2: 7 flat cells for 55 walkers), 445 (counts 170/200, pass 2), 690 (side 2 flag
# at 16,16), 775 (200 + 200 walkers for 399 entity records: the array runs out). Prints one line per battle and
#   people natural: <k>/4 battles equal; no-second-pass control equal on <c>/4
# Run from anywhere:  bash reversing/populous2/py/people/gate_battles.sh [outdir]
set -e
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done; cd "$d"
OUT=${1:-scratchpad/populous2/people_battles}
B="290 445 690 775"
mkdir -p "$OUT"
for n in $B; do
  { bash reversing/populous2/py/gen_entry.sh "$OUT/g${n}_entry.snap" "$n" > "$OUT/g$n.log" 2>&1 &&
    uv run python reversing/populous2/py/people/people_gate.py --natural --entry "$OUT/g${n}_entry.snap" > "$OUT/people_$n.out" 2>&1; } &
done
wait
ok=0; c=0
for n in $B; do
  grep -E '^battle|^placed|^natural' "$OUT/people_$n.out" | tr '\n' ' '; echo
  grep -q '^TOTAL 1/1' "$OUT/people_$n.out" && ok=$((ok + 1))
  grep -q "^control 'no second pass': equal in 1/1" "$OUT/people_$n.out" && c=$((c + 1))
done
echo "people natural: $ok/4 battles equal; no-second-pass control equal on $c/4"
