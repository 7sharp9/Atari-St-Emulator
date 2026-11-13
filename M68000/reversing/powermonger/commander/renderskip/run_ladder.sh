#!/bin/bash
# run_ladder.sh <outdir>: the state-equality ladder. For each start snapshot, every arm to tick rungs 1,10,100,300,1000
# with full-RAM dumps (base twice, as base_a and base_b, for the determinism control), the negative controls to 100.
# At most 4 emulators at once. Then compare.py every arm against base_a at every rung into <outdir>/compare.jsonl.
set -u
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; export ATARI_NOTRACE=1
O=$1; mkdir -p "$O"
SNAPS="rand1=scratchpad/pm142/rand1.snap l2o0=scratchpad/cmd9/start/o0/final.snap m1s0=scratchpad/pm123/win/m1_s0.snap"
PY="uv run python $d/renderskip.py run"
{
for sv in $SNAPS; do
  n=${sv%%=*}; s=${sv#*=}
  echo "$s base $O/$n --rungs 1,10,100,300,1000 --dump --tag base_a"
  echo "$s base $O/$n --rungs 1,10,100,300,1000 --dump --tag base_b"
  for a in f898 gated draw drawall divider; do echo "$s $a $O/$n --rungs 1,10,100,300,1000 --dump"; done
  for a in neg_1abaa neg_3e06; do echo "$s $a $O/$n --rungs 1,10,100 --dump"; done
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
