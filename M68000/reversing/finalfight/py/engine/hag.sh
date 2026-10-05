#!/bin/sh
# hag.sh <name> <plan> <frames> [VAR=val ...] : Haggar (state dch2_1900 of the twoplayer harness) from the plan py/twoplayer/py/char/plans/<plan>.lua, extra_hag.lua taps -> out/<name>/taps.txt
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
tp=$root/reversing/finalfight/py/twoplayer
name=$1; plan=$2; n=$3; shift 3
export FFD_RUN=$base/runs/run_$name FFD_OUT=$base/out/$name
mkdir -p "$FFD_RUN/sta/ffightuc" "$FFD_OUT"
cp -n $root/scratchpad/finalfight/twoplayer/run_p/sta/ffightuc/dch2_1900.sta "$FFD_RUN/sta/ffightuc/"
export HAG_TAPS="$FFD_OUT/taps.txt"
env FF_GOD=1 FF_EXTRA=$here/extra_hag.lua FF_DX=26 "$@" sh $tp/run/crun.sh log 2 $plan $n
