#!/bin/sh
# sp.sh <tag> <spawns> <rel_stop> [extra env assignments...]: one spawn.lua run from ff_enemies (FF_LOAD overrides), log to $FF_E_OUT/<tag>.log
# FF_E_OUT (outputs, default scratchpad/finalfight/p3/e/out) and FF_E_RUN (MAME run dir, default scratchpad/finalfight/p3/e/run) are read by ffrun.sh
tag=$1; spawns=$2; stop=$3; shift 3
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}
mkdir -p "$out"
env FF_LOAD=${FF_LOAD:-ff_enemies} FF_STOP=99999 FF_REL_STOP=$stop FF_KILL=${FF_KILL:-1} FF_SPAWNS="$spawns" FF_LOG=$out/$tag.log FF_OUT=$out FF_TAG=$tag "$@" $here/ffrun.sh $here/spawn.lua 300 2>&1 | tail -1
