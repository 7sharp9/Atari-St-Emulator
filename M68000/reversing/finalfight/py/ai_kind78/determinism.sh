#!/bin/sh
# determinism.sh: the same spawn run in two MAME processes must give a byte-identical log (md5 printed twice).
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}
for t in det_a det_b; do
  "$here/sp.sh" $t "8:0:0:60:47" 300 FF_SPAWN_AT=30 FF_PLAN2="$here/plan_hit.lua" >/dev/null
  md5 -q "$out/$t.log" 2>/dev/null || md5sum "$out/$t.log" | cut -d' ' -f1
done
