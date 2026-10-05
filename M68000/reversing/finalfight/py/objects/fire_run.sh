#!/bin/sh
# fire_run.sh <tag> <dx_player decimal signed> [fighter dx decimal signed | none] [fire start rel, default 200]
# Hand-spawned fire (pool a kind $10, through the pool a allocator, +0=1, x, y, +19) at x=$1c0 y=$36 from state sb_s1 at rel 200; player 1 pinned at fire.x + dx (y $36);
# optional pool-2 kind 0 fighter (Bred) pinned at fire.x + fdx, y $36. Log: out/<tag>.log. Analyse with fire_check.py.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
tag=$1; dx=$2; fdx=${3:-none}; at=${4:-200}
fx=448
px=$(printf '%x' $(( fx + dx )))
spawns="$at:a:10:0:0:1c0:36"
pin="$(( at - 10 ))-420:P:$px:36"
if [ "$fdx" != none ]; then
  fpx=$(printf '%x' $(( fx + fdx )))
  spawns="$spawns,$at:2:0:0:0:$fpx:36"
  pin="$pin,$at-420:2:$fpx:36"
fi
FFA_RUN=$run FFA_LOAD=sb_s1 FFA_LOG=$out/$tag.log FFA_STOP=$(( at + 220 )) FFA_KILL=$at FFA_SPAWNS="$spawns" FFA_PIN="$pin" FFA_POOLS="P:ff8568:c0:1" FFA_TAG=$tag \
  "$here/run.sh" "$here/sp.lua" 2>&1 | tail -1
