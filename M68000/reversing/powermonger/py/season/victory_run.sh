#!/bin/bash
# End-of-land verdict $d2c8 -> $1a4da victory screen ($57fce poked to 4, as pm122 win.cmds) and, with "final",
# the finale branch ($2df6e = 4 and $580a4 = $c2 -> $1a486 -> $1a648). Usage: victory_run.sh <tag> [normal|final] [bp-steps]
# Output $SEASON_OUT/<tag>.txt: the bp hit of $1a4da (step 790), then $1a2bc (fade-in, 1,246,622 steps after) or, final, $1a648.
ROOT="${M68000_ROOT:-$(cd "$(dirname "$0")/../../../.." && pwd)}"; cd "$ROOT" || exit 1
TAG=$1; MODE=${2:-normal}; N=${3:-10000000}
OUT=${SEASON_OUT:-scratchpad/season}; mkdir -p "$OUT"
{
# the snapshot has no disk mounted: without this $1bd0e -> $d574 fails and loops at $1bd30 (retry/insert-disk prompt)
echo "disk scratchpad/powermonger.st"
echo "w 57fcc 03b70004"
[ "$MODE" = final ] && printf 'w 2df6e 00040000\nw 580a4 00c2000a\n'
echo "bp 1a4da 20000"
echo "bp 1a2bc $N"
echo "bp 1a648 $N"
echo "q"
} > "$OUT/$TAG.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm122/end/lose_d2c8.snap repl < "$OUT/$TAG.cmds" > "$OUT/$TAG.txt" 2>&1
