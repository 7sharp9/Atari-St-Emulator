#!/bin/sh
# run.sh <name> <plan> <frames> [env assignments...]  -> $FFP_OUT/<name>.txt  (pdrive log), <name>.err
# Defaults: ff_enemies, FF_KILL=1 FF_KEEP=11 (Dug) FF_EHP=0300 FF_HEAL=30, enemy log extra. Override by passing VAR=value after the frame count.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
OUT=${FFP_OUT:-$root/scratchpad/finalfight/p3/f/out}; export FFP_OUT=$OUT; mkdir -p "$OUT"
name=$1; plan=$2; n=$3; shift 3
export PD=$here
env FF_LOAD=${FF_LOAD:-ff_enemies} FF_KILL=${FF_KILL:-1} FF_KEEP=${FF_KEEP:-11} FF_EHP=${FF_EHP:-0300} FF_HEAL=${FF_HEAL:-30} \
    FF_EXTRA=${FF_EXTRA:-$here/extra_enemy.lua} FF_N=$n FF_PLAN=$here/plans/$plan.lua FF_LOG=$OUT/$name.txt \
    FF_POKES=${FF_POKES:-$here/pokes_grab.lua} "$@" $here/ffrun.sh $here/${DRV:-pdrive.lua} 400 > $OUT/$name.err 2>&1
tail -1 $OUT/$name.err
