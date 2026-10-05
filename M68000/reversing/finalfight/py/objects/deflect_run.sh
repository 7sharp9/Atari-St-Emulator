#!/bin/sh
# deflect_run.sh <tag> <x offset dec from player> <height dec above ground> : a pool 6 kind 4 bottle hand-spawned at rel 200 at player.x + offset, y = ground + height, +14 = ground ($36),
# in its flight step (state 2 mode 0 step 2, set by the handler); vx, vy, gravity held at 0 for rel 201-234 so it hovers; player 1 pinned at x $1c0 y $36; Button 1 pressed at rel 230.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
tag=$1; off=$2; ht=$3
bx=$(printf '%x' $(( 448 + off ))); by=$(printf '%x' $(( 54 + ht )))
FFA_RUN=$run FFA_LOAD=sb_s1 FFA_LOG=$out/$tag.log FFA_STOP=${DF_STOP:-420} FFA_KILL=200 FFA_SPAWNS="200:6:4:0:0:$bx:$by" \
 FFA_POKES="201:@14:0036:2" FFA_HOLD="202-233:1:80:0:2,202-233:1:82:0:2,202-233:1:84:0:2,202-233:1:86:0:2" FFA_PIN="190-300:P:1c0:36" FFA_PLAN2=$here/plan_b1.lua FFA_POOLS="P:ff8568:c0:1" FFA_TAG=$tag \
  "$here/run.sh" "$here/sp.lua" 2>&1 | tail -1
