#!/bin/sh
# kind7.sh: six kind-7 spawns at different frames; each record lives delay+2 frames (handler $3c446 count = delay + 2).
# Output: $FF_E_OUT/k7c_<i>.log/.hits, then a one-line summary per run.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}
for i in 1 2 3 4 5 6; do
  "$here/sp.sh" k7c_$i "7:0:0:90:47" 130 FF_SPAWN_AT=$((3+i*5)) FF_MAMEARGS="-debug -debugger none" FF_ADDRS=3c446,3c45a,3c47e,3c48a FF_HIT_OUT="$out/k7c_$i.hits" >/dev/null
  printf 'run %s: ' $i; paste -sd' ' "$out/k7c_$i.hits"
done
