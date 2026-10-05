#!/bin/sh
# pick_run.sh <tag> <pool 6 kind hex> [+20 hex] : player 1 pinned at x $1c0 y $36 (sb_s1, rel 190-330), one weapon of that kind spawned through the pool 6 allocator on his feet
# at rel 200 (x $1c0, y $36), Button 1 pressed at rel 230 for 8 frames. Log out/<tag>.log; pick_check.py reads player +90 (held weapon) and the weapon's +64/+74/+66.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
tag=$1; kind=$2; b20=${3:-0}
FFA_RUN=$run FFA_LOAD=sb_s1 FFA_LOG=$out/$tag.log FFA_STOP=300 FFA_KILL=200 FFA_SPAWNS="200:6:$kind:$b20:0:1c0:36" FFA_PIN="190-300:P:1c0:36" FFA_PLAN2=$here/plan_b1.lua FFA_POOLS="P:ff8568:c0:1" FFA_TAG=$tag \
  "$here/run.sh" "$here/sp.lua" 2>&1 | tail -1
