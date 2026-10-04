#!/usr/bin/env bash
# batch3: extend the lands with the fastest-draining AI groups from their 2G snapshots by 10G more steps (40 x 250M), same hits list as run_arms2.sh.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
ARMS=${ARMS_WORK:-scratchpad/pm148/arms}   # work dir (default named here): long/ (chunk snapshots, hits txt), sheep/, lands2/, natgate/
PYA=reversing/powermonger/py/arms
for l in k143 k25 k40 k44; do
  bash $PYA/run_arms2.sh $ARMS/long/L2G_${l}_c8.snap X10G_$l 40 250000000 &
done
wait
echo done > $ARMS/long/batch3.done
