#!/usr/bin/env bash
# batch2: build 36 new Play Random Land lands (k = 2, 6, ..., 142; PAGES0=1, build_land.sh), then run each 8 x 250M steps with the extended hits list.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
ARMS=${ARMS_WORK:-scratchpad/pm148/arms}   # work dir (default named here): long/ (chunk snapshots, hits txt), sheep/, lands2/, natgate/
PYA=reversing/powermonger/py/arms
mkdir -p $ARMS/lands2 $ARMS/long; export PM_WORK=$ARMS/lands2 PAGES0=1
seq 2 4 142 | xargs -P 8 -I{} bash reversing/powermonger/py/build_land.sh {} > $ARMS/lands2/build.log 2>&1
ls $ARMS/lands2/k*.snap | xargs -n1 basename | sed 's/.snap//' > $ARMS/lands2.txt
cat $ARMS/lands2.txt | xargs -P 12 -I{} bash $PYA/run_arms2.sh $ARMS/lands2/{}.snap M2G_{} 8 250000000
echo done > $ARMS/long/batch2.done
