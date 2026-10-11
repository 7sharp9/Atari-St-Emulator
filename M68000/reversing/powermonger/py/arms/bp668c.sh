#!/usr/bin/env bash
# bp668c.sh <tag> <chunk-snap> <steps-to-668c>: stop at the natural transfer arm $668c, snapshot there, then run to $1c18 (the men move)
# and snapshot at it and 20000 steps after. Output: $PM_WORK/x/<tag>_bp.txt and <tag>_at668c / _at1c18 / _after1c18 .snap
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$HERE; while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm150/arms}/x; mkdir -p "$W"
t=$1; s=$2; n=$3
printf "disk scratchpad/powermonger.st\nbp 668c $(( n + 1000 ))\nsnap $W/${t}_at668c.snap\nm 58016 8\nbp 1c18 30000000\nsnap $W/${t}_at1c18.snap\ns 20000\nsnap $W/${t}_after1c18.snap\nq\n" > "$W/${t}_bp.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$s" repl < "$W/${t}_bp.cmds" > "$W/${t}_bp.txt" 2>&1
