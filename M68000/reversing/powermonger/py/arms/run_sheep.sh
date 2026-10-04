#!/usr/bin/env bash
# run_sheep.sh <land> <cx> <cy> <leadhex> <tag>: sword icon + minimap click on a sheep cell of pm143/lands/<land>.snap, 16 x 1M steps with hits and a snapshot per chunk.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
ARMS=${ARMS_WORK:-scratchpad/pm148/arms}   # work dir (default named here): long/ (chunk snapshots, hits txt), sheep/, lands2/, natgate/
PYA=reversing/powermonger/py/arms
. .venv/bin/activate
land=$1; cx=$2; cy=$3; lead=$4; tag=$5
d=$ARMS/sheep; mkdir -p $d
python $PYA/drive_sheep2.py scratchpad/pm143/lands/$land.snap $cx $cy $d/${land}_$tag.cmds 16 1000000 516c0 $lead
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm143/lands/$land.snap repl < $d/${land}_$tag.cmds 2>&1 | grep -v "^mouse\|first -1" > $d/${land}_$tag.txt
echo "== $land $tag"
python $PYA/modes_scan.py $d/${land}_${tag}_c*.snap | cut -c1-260
