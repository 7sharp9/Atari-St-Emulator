#!/bin/bash
# finale_frames.sh <tag>: victory_run.sh's "final" pokes ($57fce 4 at $d2c8, $2df6e = 4, $580a4 = $c2) from
# pm122/end/lose_d2c8.snap with the disk mounted, then a snapshot at $1a6a6 (resources $c/$d drawn, before the
# frames), at $1a6d4 after each of the 7 flips ($187a), and at $1a766 (the closing text drawn). PNGs via snap_render.py.
# Output $PM_WORK/finale (default scratchpad/season/finale). Run from anywhere; finds M68000/ by tools/rdis.py.
# Then: uv run python reversing/powermonger/py/season/finale_delta.py <out dir> <tag> (7 of 7 frames, 0 bytes differ).
ROOT=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); done; cd "$ROOT" || exit 1
TAG=${1:-fin}; OUT=${PM_WORK:-scratchpad/season}/finale; mkdir -p "$OUT"
{
echo "disk scratchpad/powermonger.st"
echo "w 57fcc 03b70004"
printf 'w 2df6e 00040000\nw 580a4 00c2000a\n'
echo "bp 1a4da 20000"
echo "bp 1a648 10000000"
echo "bp 1a6a6 20000000"; echo "m 3f768 64"; echo "snap $OUT/${TAG}_base.snap"
for i in 1 2 3 4 5 6 7; do echo "bp 1a6d4 5000000"; echo "r"; echo "snap $OUT/${TAG}_f$i.snap"; done
echo "bp 1a766 5000000"; echo "snap $OUT/${TAG}_text.snap"
echo "q"
} > "$OUT/$TAG.cmds"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm122/end/lose_d2c8.snap repl < "$OUT/$TAG.cmds" > "$OUT/$TAG.txt" 2>&1
grep -E "breakpoint|gave up|PC=" "$OUT/$TAG.txt" | head -30
for f in "$OUT"/${TAG}_*.snap; do uv run python tools/snap_render.py "$f" "${f%.snap}.png"; done
