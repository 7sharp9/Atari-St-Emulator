#!/usr/bin/env bash
# natrun66.sh <snap> <tag> <steps> [extra REPL lines file]: no pokes (adapted from pm153 modes/py/natrun.sh). Watch every
# object-record write and keep the writes from the $66 route and its competitors: $5106 (prev $66), $161f0 (water veto,
# mode $00), $14c9a ($00 -> $8c afloat with a Boat), $14caa ($00 -> $0a), $14e36/$14e44 ($0a -> $08 / $10), $14c66
# (landing -> $10), $14fdc (arrival: mode := prev), $36ec/$36f2 (camp $35f4: mode $10 / prev $20), $1540c ($66 handler).
# Output: $PM_WORK/run/<tag>.out (hits) and <tag>.watch (filtered WATCH lines). Success: a WATCH `pc=$014fdc ... <- $66`.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$HERE}
while [ ! -f "$ROOT/tools/rdis.py" ]; do ROOT=$(dirname "$ROOT"); [ "$ROOT" = / ] && { echo "no repo root"; exit 1; }; done
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm156}/modes66/run; mkdir -p "$W"
snap=$1; tag=$2; steps=$3
{ printf 'disk scratchpad/powermonger.st\nwatch 51b66 25600\n'; [ -n "$4" ] && cat "$4"
  printf 'hits %s 5100 5106 161f0 14c9a 14caa 14e36 14e44 14c66 14fdc 1540c 36ec 35f4 1547e\nq\n' "$steps"; } > "$W/$tag.repl"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$snap" repl < "$W/$tag.repl" \
  2> >(grep -E 'pc=\$(014fdc|005106|0161f0|014c9a|014caa|014e36|014e44|014c66|0036ec|0036f2|01540c)' > "$W/$tag.watch") > "$W/$tag.out"
wait
echo "$tag arr66=$(grep -c '014fdc.*<- \$66$' "$W/$tag.watch") prev66=$(grep -c '005106' "$W/$tag.watch") h1540c=$(grep '\$01540c' "$W/$tag.out" | awk '{print $2}')"
