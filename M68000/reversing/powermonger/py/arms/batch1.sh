#!/usr/bin/env bash
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
ARMS=${ARMS_WORK:-scratchpad/pm148/arms}   # work dir (default named here): long/ (chunk snapshots, hits txt), sheep/, lands2/, natgate/
PYA=reversing/powermonger/py/arms
ls scratchpad/pm143/lands/*.snap | xargs -n1 basename | sed "s/.snap//" | xargs -P 12 -I{} bash $PYA/run_arms.sh scratchpad/pm143/lands/{}.snap L2G_{} 8 250000000
echo done > $ARMS/long/batch1.done
