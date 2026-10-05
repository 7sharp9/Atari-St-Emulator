#!/bin/sh
# prun.sh <name> <state> <plan> <frames> [VAR=value ...] : pvp.lua from a two-player state; log $FFD_OUT/<name>.txt
d=$(cd "$(dirname "$0")/.." && pwd)
. "$d/run/env.sh"
name=$1; st=$2; plan=$3; n=$4; shift 4
env FF_DIR=$d/lua FF_OUT=$out FF_LOAD=$st FF_PLAN=$d/py/pvp/plans/$plan.lua FF_N=$n FF_LOG=$out/$name.txt FF_KILL=${FF_KILL:-1} "$@" sh $d/run/ffrun.sh $d/lua/pvp.lua 300 > $out/$name.err 2>&1
tail -1 $out/$name.err
