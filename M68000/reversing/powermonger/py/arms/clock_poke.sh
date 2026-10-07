#!/usr/bin/env bash
# clock_poke.sh <src.snap> <tag> <clock-hex-word|none> <steps> : one run from <src.snap> with the sim clock word `$2df72` poked
# (a longword write `<word>0000`: the word at `$2df74` is 0 in these snapshots) and `hits` on the camp-wait decision `$65b4`
# (the first instruction after the signed compare `cmp.w $2df72,D0 / bgt $66c8` at `$65a0`), `$6522` and `$66e8`.
# Isolates the signed-clock stall: the only thing that differs between runs from one snapshot is the poke.
# Output ($ARMS_WORK, default scratchpad/pm149/clock): <tag>.cmds, <tag>.txt
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
OUT=${ARMS_WORK:-scratchpad/pm149/clock}   # work dir (default named here)
mkdir -p "$OUT"
src=$1; tag=$2; clk=$3; steps=$4
{
  echo "disk scratchpad/powermonger.st"
  [ "$clk" != none ] && echo "w 2df72 ${clk}0000"
  echo "hits $steps 65b4 6522 66e8"
  echo "m 2df72 2"
  echo q
} > "$OUT/$tag.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$src" repl < "$OUT/$tag.cmds" > "$OUT/$tag.txt" 2>&1
echo "$tag done"
