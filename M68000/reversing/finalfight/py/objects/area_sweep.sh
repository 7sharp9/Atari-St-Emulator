#!/bin/sh
# area_sweep.sh <tag> <stage hex> <area hex> <x0 hex> <x1 hex> <frames dec> [y hex] [shots "rel,rel,.."] [gfx on|off]
# From sb_s1: poke 190/191 := stage/area and the phase word 0(A5) := 4 (area init, transitions.md) at rel 1; at rel 150 sweep player 1 from x0 to x1 over <frames>
# frames with every pool-2 record cleared and the camera lock 278(A5) cleared each frame (FFA_KILLALL), right limit 1078(A5) = $2f00 (FFA_LIMIT), health refilled.
# Logs pools 8, a, 6, 4, 12, 14, 2 (changes only) and, if gfx is on, a hash of palette RAM and the three scroll maps per frame. Output out/<tag>.log; hist8.py reads it.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
tag=$1; st=$2; ar=$3; x0=$4; x1=$5; n=$6; y=${7:-50}; shots=${8:-}; gfx=${9:-on}
stop=$(( 150 + n + 60 ))
G=""; [ "$gfx" = on ] && G="pal:914000:1800,scr1:908000:4000,scr2:90c000:4000,scr3:910000:4000"
FFA_RUN=$run FFA_LOAD=sb_s1 FFA_LOG=$out/$tag.log FFA_STOP=$stop FFA_POKES="1:ff80be:$st:1,1:ff80bf:$ar:1,1:ff8000:0004:2" FFA_SWEEP="150-$(( 150 + n )):$x0:$x1:$y" \
 FFA_LIMIT=${LIMIT:-2f00} FFA_KILLALL=${KILLFROM:-120}-$stop FFA_HEAL=1 FFA_GFX="$G" FFA_SHOT="$shots" FFA_TAG=$tag "$here/run.sh" "$here/sp.lua" 2>&1 | tail -1
