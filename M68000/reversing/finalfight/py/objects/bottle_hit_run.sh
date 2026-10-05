#!/bin/sh
# bottle_hit_run.sh <tag> <press rel> : as bottle_run.sh bt1 (thrower spawned at rel 200, camera + $90) with Button 1 held for 8 frames from <press rel>
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
tag=$1; pr=$2
printf 'return { {%s, "b1", 1}, {%s, "b1", 0} }\n' "$pr" "$(( pr + 8 ))" > "$out/$tag.plan.lua"
FFA_RUN=$run FFA_LOAD=sb_s1 FFA_LOG=$out/$tag.log FFA_STOP=450 FFA_KILL=200 FFA_SPAWNS="200:2:8:0:0:c+90:30" FFA_PLAN2=$out/$tag.plan.lua FFA_POOLS="P:ff8568:c0:1" FFA_TAG=$tag \
  "$here/run.sh" "$here/sp.lua" 2>&1 | tail -1
