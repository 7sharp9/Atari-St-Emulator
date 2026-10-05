#!/bin/sh
# runids.sh <char> <dx> [frames] [approach] [f161]: one fresh run per attack id 0..15 (forced at rel 60 against an idle Cody),
# tags id<char>_<id> in $K6_RUN_DIR. Needs the state k6_pre (make_pre.sh). Analysis: summ2.py, gate_dmg.py.
dir=$(cd "$(dirname "$0")" && pwd)
for i in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  K6_APPROACH=${4:-1} K6_F161=${5:-0} K6_TAG=id$1_$i K6_FRAMES=${3:-400} K6_IMMORTAL=1 K6_SPAWN="$1:0:340:48" K6_FORCE="60:$i:$2" \
    "$dir/ffrun_k6.sh" "$dir/k6run.lua" 60 > /dev/null 2>&1
done
