#!/bin/sh
# forced.sh: mode-6 (hit reaction) sub-machines, one run per reaction id (63(A6)) poked into a live kind-8 record at rel 36,
# hp raised to $400 (alive) or -1 (dies in the knockdown paths).  Output out/f_<id>[d].log/.hits
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}
mkdir -p "$out"
ADDRS=$(cat "$here/addrs.txt")
for id in 0 1 2 3 4 5 6 7 8 14; do
  P="36:@3:06:1,36:@4:00:1,36:@5:00:1,36:@63:$(printf %02x $id):1,36:@24:0400:2,36:@26:0400:2,36:@28:0400:2,36:@62:01:1"
  "$here/sp.sh" f_$id "8:0:0:30:47" 330 FF_SPAWN_AT=30 FF_POKES="$P" FF_MAMEARGS="-debug -debugger none" FF_ADDRS="$ADDRS" FF_HIT_OUT="$out/f_$id.hits" >/dev/null
  echo "id $id done"
done
for id in 3 5 6 8; do
  P="36:@3:06:1,36:@4:00:1,36:@5:00:1,36:@63:$(printf %02x $id):1,36:@24:ffff:2,36:@26:0400:2,36:@28:0400:2,36:@62:01:1"
  "$here/sp.sh" f_${id}d "8:0:0:30:47" 330 FF_SPAWN_AT=30 FF_POKES="$P" FF_MAMEARGS="-debug -debugger none" FF_ADDRS="$ADDRS" FF_HIT_OUT="$out/f_${id}d.hits" >/dev/null
  echo "id $id dead done"
done
