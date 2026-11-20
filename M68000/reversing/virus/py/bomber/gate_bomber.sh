#!/bin/bash
# Gate `bomber`: model vs the emulator on stamped natural captures (about 40 s each x 10, one emulator) and the 25 saved pursuer
# captures, with seven broken-model controls. `gate_bomber.sh nocap` skips the captures (reuses $VIRUS_WORK/bomber/caps).
# Output: $VIRUS_WORK/bomber/out.txt and gate_out.txt (default scratchpad/virus/bomber/). Run from anywhere; the repo root is found by walking up.
H="$(cd "$(dirname "$0")" && pwd)"; d="$H"; while [ ! -f "$d/tools/rdis.py" ]; do d="$(dirname "$d")"; [ "$d" = / ] && exit 9; done; cd "$d"
W="${VIRUS_WORK:-scratchpad/virus}"; O="${BOMBER_OUT:-$W/bomber}"; mkdir -p "$O/caps"
if [ "$1" != nocap ]; then BOMBER_OUT="$O/caps" bash "$H/capture_all.sh" || exit 1; fi
{
  echo "== stamped, model"; uv run python "$H/gate_bomber.py" stamped "$O"/caps/b_*.json
  echo "== corpus (25 natural pursuer captures), model"; uv run python "$H/gate_bomber.py" corpus "$W"/pursuer/caps/nat_*.json
  for c in swapaxes spring6c spring4 every16 jit12 jit5 always51; do
    echo "== stamped, control $c"; uv run python "$H/gate_bomber.py" stamped "$O"/caps/b_*.json --control $c | grep -v '^  miss'
  done
  for c in swapaxes spring6c every16; do
    echo "== corpus, control $c"; uv run python "$H/gate_bomber.py" corpus "$W"/pursuer/caps/nat_*.json --control $c | grep -v '^  miss'
  done
} > "$O/out.txt" 2>&1
grep -v '^  miss' "$O/out.txt" | tee "$O/gate_out.txt"
