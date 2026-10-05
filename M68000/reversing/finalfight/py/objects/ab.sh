#!/bin/sh
# ab.sh <tag> <stage hex> <area hex> <park x hex> <frames> <hide addrs, + separated> <gfx regions> : parked-camera A/B. From sb_s1 poke the area, park player 1 at <park x> y $50 from
# rel 100 (pool 2 cleared, camera lock cleared), and run <frames> frames with the gfx regions hashed. Run A leaves everything alone; run B zeroes +0 of the listed pool 8 records
# at rel 2 (they never run). Output out/<tag>_A.log and _B.log; ab_count.py counts the G lines of a window.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
tag=$1; st=$2; ar=$3; px=$4; n=$5; hide=$6; G=${7:-scr2:90c000:4000,scr3:910000:4000,pal:914000:1800}
for v in A B; do
  H=""; [ $v = B ] && H="12:$hide"
  FFA_RUN=$run FFA_LOAD=sb_s1 FFA_LOG=$out/${tag}_$v.log FFA_STOP=$n FFA_POKES="1:ff80be:$st:1,1:ff80bf:$ar:1,1:ff8000:0004:2" FFA_SWEEP="100-101:$px:$px:50" FFA_HOLDA="102-$n:ff856e:$px:2" \
   FFA_KILLALL=60-$n FFA_LIMIT=2f00 FFA_HEAL=1 FFA_GFX="$G" FFA_HIDE="$H" FFA_SHOT=$(( n - 2 )) FFA_TAG=${tag}_$v "$here/run.sh" "$here/sp.lua" 2>&1 | tail -1
done
