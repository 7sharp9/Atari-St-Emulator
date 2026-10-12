#!/usr/bin/env bash
# routrun.sh <snap> <tag> <steps>: rerun of the pm153 rout_fate runs (rt_rand1 / rt_k48: watch 51b66 25600, hits over
# <steps>) keeping every write that starts at record offsets 0..7 or 28..31 (wfilter.py), not just a few pcs.
# Output: ${PM_WORK:-scratchpad/pm156}/rout/run/<tag>.out (hits) and <tag>.watch (filtered WATCH lines).
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm156}/rout/run; mkdir -p "$W"
snap=$1; tag=$2; steps=$3
printf 'disk scratchpad/powermonger.st\nwatch 51b66 25600\nhits %s 561c 1bea 14fdc 15598 5708\nq\n' "$steps" > "$W/$tag.repl"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl < "$W/$tag.repl" \
  2> >(python3 "$HERE/wfilter.py" > "$W/$tag.watch") > "$W/$tag.out"
wait
sleep 2
echo "$tag done: $(wc -l < "$W/$tag.watch") watch lines"
