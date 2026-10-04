#!/usr/bin/env bash
# batch4: k80 and k108 (the lands whose AI group 0 re-decides every tick) from their 2G snapshots for 5G more steps: does the camp wait `256(A1)+$14 > $2df72` (signed word clock) stall them at tick 32768 (about 5.4G steps)?
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
ARMS=${ARMS_WORK:-scratchpad/pm148/arms}   # work dir (default named here): long/ (chunk snapshots, hits txt), sheep/, lands2/, natgate/
PYA=reversing/powermonger/py/arms
for l in k80 k108; do
  bash $PYA/run_arms2.sh $ARMS/long/L2G_${l}_c8.snap W5G_$l 20 250000000 &
done
wait
echo done > $ARMS/long/batch4.done
