#!/bin/bash
# run_orders.sh <outdir>: the equality ladder with injected orders. rand1 (side 3 taken, attack $0c on (15,92), as
# gate_inject.sh) and l2o0 (the first four decisions of the cmd9 rollout run o0, side 1, at ticks 0..348), each with
# arms base (twice), f898, drawall and divider to tick rungs 1,10,100,300,1000 with dumps, then compare.py against
# base_a into <outdir>/compare.jsonl. The no-order ladder's base_a (run_ladder.sh) is the "did the orders do
# anything" reference: compare it with this base_a by hand (README).
set -u
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; export ATARI_NOTRACE=1
O=$1; mkdir -p "$O"
SNAPS="rand1=scratchpad/pm142/rand1.snap l2o0=scratchpad/cmd9/start/o0/final.snap"
PY="uv run python $d/renderskip.py run"
{
for sv in $SNAPS; do
  n=${sv%%=*}; s=${sv#*=}; A="--actions $d/actions_$n.json"
  echo "$s base $O/$n --rungs 1,10,100,300,1000 --dump --tag base_a $A"
  echo "$s base $O/$n --rungs 1,10,100,300,1000 --dump --tag base_b $A"
  for a in f898 drawall divider; do echo "$s $a $O/$n --rungs 1,10,100,300,1000 --dump $A"; done
done
} > "$O/jobs.txt"
xargs -P 4 -L 1 $PY < "$O/jobs.txt" > "$O/runs.log" 2> "$O/runs.err"
: > "$O/compare.jsonl"
for sv in $SNAPS; do
  n=${sv%%=*}
  for f in "$O/$n"/*_k*.ram; do
    b=$(basename "$f" .ram); tag=${b%_k*}; k=${b##*_k}
    [ "$tag" = base_a ] && continue
    ign=""; [ "$tag" = divider ] && ign="--ignore 57fee:4"
    printf '{"snap":"%s","tag":"%s","k":%s,"cmp":' "$n" "$tag" "$k" >> "$O/compare.jsonl"
    python3 "$d/compare.py" "$O/$n/base_a_k$k.ram" "$f" --json $ign | tr -d '\n' >> "$O/compare.jsonl"
    echo '}' >> "$O/compare.jsonl"
  done
done
echo done > "$O/DONE"
