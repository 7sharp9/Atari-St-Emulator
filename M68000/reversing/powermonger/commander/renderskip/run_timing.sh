#!/bin/bash
# run_timing.sh <outdir> [rounds] [ticks]: interleaved wall-time runs, one emulator at a time. Per start snapshot and
# round, arms base, f898, gated, drawall run to <ticks> (default 1000) tick arrivals with no dumps; the arm order is
# rotated by one each round so no arm always runs first. Each run's row (steps, wall_s, uptime) goes to
# <outdir>/<snap>/<arm>_r<round>.jsonl; summarise with timing_summary.py <outdir>.
set -u
d=$(cd "$(dirname "$0")" && pwd); R=$d; while [ ! -f "$R/tools/rdis.py" ]; do R=$(dirname "$R"); done
cd "$R"; export ATARI_NOTRACE=1
O=$1; ROUNDS=${2:-3}; T=${3:-1000}; mkdir -p "$O"
SNAPS="rand1=scratchpad/pm142/rand1.snap l2o0=scratchpad/cmd9/start/o0/final.snap m1s0=scratchpad/pm123/win/m1_s0.snap"
ARMS=(base f898 gated drawall)
for r in $(seq 1 "$ROUNDS"); do
  for sv in $SNAPS; do
    n=${sv%%=*}; s=${sv#*=}
    for i in 0 1 2 3; do
      a=${ARMS[$(( (i + r) % 4 ))]}
      uv run python "$d/renderskip.py" run "$s" "$a" "$O/$n" --rungs "$T" --tag "${a}_r$r" >> "$O/runs.log" 2>> "$O/runs.err"
    done
  done
done
echo done > "$O/DONE"
