#!/bin/sh
# bottle_run.sh <tag> <spawn rel> [x offset from camera hex, default 90] : state sb_s1, pool 2 killed and one kind 8 (fire-bottle thrower, +20 0) spawned through the
# tag-2 allocator at rel <spawn rel>, camera + offset, y $30; player 1 left alone (health not refilled); 450 frames after the spawn. Log out/<tag>.log -> bottle_check.py.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
tag=$1; at=$2; off=${3:-90}
FFA_RUN=$run FFA_LOAD=sb_s1 FFA_LOG=$out/$tag.log FFA_STOP=$(( at + 450 )) FFA_KILL=$at FFA_SPAWNS="$at:2:8:0:0:c+$off:30" FFA_POOLS="P:ff8568:c0:1" FFA_TAG=$tag \
  "$here/run.sh" "$here/sp.lua" 2>&1 | tail -1
