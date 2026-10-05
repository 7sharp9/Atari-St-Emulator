#!/bin/sh
# crun.sh <name> <ch> <plan> <frames> [VAR=value ...] : from state dch<ch>_1900 (character <ch> selected on the real select screen, Bred spawning, frame 1900),
# run pdrive.lua with plan py/char/plans/<plan>.lua; log $FFD_OUT/<name>.txt. Defaults as py/player/run.sh: Bred (record 12) kept, hp $300, healed, a dummy next to P1.
d=$(cd "$(dirname "$0")/.." && pwd)
. "$d/run/env.sh"
name=$1; ch=$2; plan=$3; n=$4; shift 4
export PD=$d/lua
env FF_DIR=$d/lua FF_OUT=$out FF_LOAD=${FF_LOAD:-dch${ch}_1900} FF_KILL=${FF_KILL:-1} FF_KEEP=${FF_KEEP:-12} FF_EHP=${FF_EHP:-0300} FF_HEAL=${FF_HEAL:-30} \
    FF_EXTRA=${FF_EXTRA:-$d/lua/extra_enemy.lua} FF_N=$n FF_PLAN=$d/py/char/plans/$plan.lua FF_LOG=$out/$name.txt \
    FF_POKES=${FF_POKES:-$d/lua/pokes_none.lua} FF_DUMMY=${FF_DUMMY:-12} "$@" sh $d/run/ffrun.sh $d/lua/pdrive.lua 400 > $out/$name.err 2>&1
tail -1 $out/$name.err
