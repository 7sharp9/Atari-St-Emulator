#!/bin/sh
# hide_run.sh <tag> <stage hex> <area hex> <hide rel> <hide addrs + separated | none> <end rel> [extra FFA_POKES entries ,..] : from sb_s1 poke the area (phase 4), run to <end rel>;
# at <hide rel> zero +0 of the listed pool records (none = reference run) and take a screenshot at <end rel> - 1. Files run/snap/<tag>_<end-1>.png. hidediff.py compares two.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
tag=$1; st=$2; ar=$3; hr=$4; hide=$5; end=$6; extra=${7:-}
HD=""; [ "$hide" != none ] && HD="$hr:$hide"
FFA_RUN=$run FFA_LOAD=sb_s1 FFA_LOG=$out/$tag.log FFA_STOP=$end FFA_POKES="1:ff80be:$st:1,1:ff80bf:$ar:1,1:ff8000:0004:2$extra" FFA_HEAL=1 FFA_HIDE="$HD" FFA_SHOT=$(( end - 1 )) FFA_TAG=$tag "$here/run.sh" "$here/sp.lua" 2>&1 | tail -1
