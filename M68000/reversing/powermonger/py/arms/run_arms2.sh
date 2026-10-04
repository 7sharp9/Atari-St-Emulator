#!/usr/bin/env bash
# run_arms.sh <src.snap> <name> <chunks> <steps-per-chunk> : natural run (no pokes), hits on the commander arms per chunk + a snapshot per chunk.
# Output ($ARMS_WORK, default scratchpad/pm148/arms): long/<name>.txt and <name>_cN.snap
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
ARMS=${ARMS_WORK:-scratchpad/pm148/arms}   # work dir (default named here): long/ (chunk snapshots, hits txt), sheep/, lands2/, natgate/
PYA=reversing/powermonger/py/arms
src=$1; name=$2; n=$3; steps=$4
d=$ARMS/long; mkdir -p $d
A="6522 65b4 65c8 65e0 65f4 661a 6638 664c 666c 6680 6686 668c 66a4 66b0 66e8 6762 6822 6884 4220 4562 2776 d2c8 5100 153cc 1547e 15518 25d6 550e"
{ echo "disk scratchpad/powermonger.st"; for i in $(seq 1 $n); do echo "hits $steps $A"; echo "snap $d/${name}_c$i.snap"; done; echo q; } > $d/$name.cmds
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $src repl < $d/$name.cmds > $d/$name.txt 2>&1
