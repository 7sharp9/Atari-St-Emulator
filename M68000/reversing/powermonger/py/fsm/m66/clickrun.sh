#!/usr/bin/env bash
# clickrun.sh <land> <cx> <cy> <prewait> <tag> <steps>: player-input only (no pokes). From scratchpad/pm143/lands/<land>.snap,
# run <prewait> steps, then the sword icon (243,190) and a minimap click on cell (cx,cy) (pixel (cx, cy+6)), the same
# input sequence as reversing/powermonger/py/arms/drive_sheep2.py; then watch the whole object array and count the $66
# route for <steps> steps (filters as natrun66.sh). Output: $PM_WORK/modes66/run/<tag>.{repl,out,watch}.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm156}/modes66/run; mkdir -p "$W"
land=$1; cx=$2; cy=$3; pre=$4; tag=$5; steps=$6
mv() { printf 'mouse move %s %s\ns 300000\nmouse move 0 0\ns 300000\n' "$1" "$2"; }
click() { printf 'mouse down l\nmouse move 0 0\ns 300000\nmouse up l\nmouse move 0 0\n'; }
{ printf 'disk scratchpad/powermonger.st\n'; [ "$pre" -gt 0 ] && printf 's %s\n' "$pre"
  mv -400 -400; mv 243 190; click; printf 's 300000\n'; mv $((cx - 243)) $((cy + 6 - 190)); click
  printf 'watch 51b66 25600\nhits %s 5100 5106 161f0 14c9a 14caa 14e36 14e44 14c66 14fdc 1540c 36ec 35f4 1547e 371a\nq\n' "$steps"; } > "$W/$tag.repl"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "scratchpad/pm143/lands/$land.snap" repl < "$W/$tag.repl" \
  2> >(grep -E 'pc=\$(014fdc|005106|0161f0|014c9a|014caa|014e36|014e44|014c66|0036ec|0036f2|00371a|01540c)' > "$W/$tag.watch") > "$W/$tag.out"
wait
echo "$tag arr66=$(grep -c '014fdc.*<- \$66$' "$W/$tag.watch") prev66=$(grep -c '005106' "$W/$tag.watch") $(grep -E '\$(005100|0161f0|014e44|0035f4|00371a) ' "$W/$tag.out" | awk '{printf "%s=%s ", $1, $2}')"
